"""
API Routes - BotBuddy
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..config import settings
from ..personality.companion import Companion
from ..memory import MemoryManager


router = APIRouter()
companion = Companion()
memory = MemoryManager()


# ==================== MODELS ====================

class ChatRequest(BaseModel):
    user_id: str
    message: str
    conversation_id: Optional[str] = None
    detected_mood: Optional[str] = None
    mood_confidence: Optional[float] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    memories_created: int


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    preferred_name: Optional[str] = None
    phone_number: Optional[str] = None
    timezone: Optional[str] = None
    morning_checkin_enabled: Optional[bool] = None
    evening_checkin_enabled: Optional[bool] = None


class CompanionSettingsRequest(BaseModel):
    name: Optional[str] = None


# ==================== CHAT ====================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message, get a response"""
    try:
        response, conversation_id, new_memories = await companion.chat(
            user_id=request.user_id,
            message=request.message,
            conversation_id=request.conversation_id,
            detected_mood=request.detected_mood,
            mood_confidence=request.mood_confidence
        )
        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            memories_created=len(new_memories)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/greeting/{user_id}")
async def get_greeting(user_id: str):
    """Get personalized greeting"""
    greeting = await companion.get_greeting(user_id)
    return {"greeting": greeting}


# ==================== USER ====================

@router.get("/user/{user_id}")
async def get_user(user_id: str):
    """Get user profile"""
    user = await memory.get_or_create_user(user_id)
    return user.model_dump()


@router.put("/user/{user_id}")
async def update_user(user_id: str, request: UserUpdateRequest):
    """Update user profile"""
    updates = request.model_dump(exclude_none=True)
    user = await companion.update_user_profile(user_id, updates)
    return user.model_dump()


# ==================== MEMORY ====================

@router.get("/memories/{user_id}")
async def get_memories(user_id: str, memory_type: Optional[str] = None, limit: int = 50):
    """Get user's memories"""
    from ..memory.models import MemoryType
    mem_type = MemoryType(memory_type) if memory_type else None
    memories = await memory.get_memories(user_id, mem_type, limit)
    return [m.model_dump() for m in memories]


@router.get("/memories/{user_id}/search")
async def search_memories(user_id: str, query: str, limit: int = 10):
    """Search memories"""
    memories = await memory.search_memories(user_id, query, limit)
    return [m.model_dump() for m in memories]


# ==================== CONVERSATIONS ====================

@router.get("/conversations/{user_id}")
async def get_conversations(user_id: str, days: int = 7, limit: int = 10):
    """Get recent conversations"""
    convos = await memory.get_recent_conversations(user_id, days, limit)
    return [c.model_dump() for c in convos]


@router.get("/conversation/{conversation_id}/messages")
async def get_messages(conversation_id: str, limit: int = 50):
    """Get conversation messages"""
    messages = await memory.get_conversation_history(conversation_id, limit)
    return [m.model_dump() for m in messages]


# ==================== SETTINGS ====================

@router.get("/settings")
async def get_settings():
    """Get companion settings"""
    return {
        "companion_name": companion.name,
        "morning_checkin_hour": settings.morning_checkin_hour,
        "evening_checkin_hour": settings.evening_checkin_hour
    }


@router.put("/settings")
async def update_settings(request: CompanionSettingsRequest):
    """Update companion settings (like name)"""
    if request.name:
        await companion.set_companion_name(request.name)
    return {"companion_name": companion.name}


# ==================== IMPORT ====================

class ImportTextRequest(BaseModel):
    user_id: str
    text: str


@router.post("/import/text")
async def import_from_text(request: ImportTextRequest):
    """Import memories from raw text (paste conversations)"""
    from ..importer import MemoryImporter

    importer = MemoryImporter(request.user_id)
    result = await importer.import_from_text(request.text)

    return {
        "memories_extracted": result.memories_extracted,
        "memories_saved": result.memories_saved,
        "errors": result.errors
    }


@router.get("/import/stats/{user_id}")
async def get_import_stats(user_id: str):
    """Get stats about imported memories"""
    from ..memory.models import MemoryType

    facts = await memory.get_memories(user_id, MemoryType.FACT, limit=100)
    prefs = await memory.get_memories(user_id, MemoryType.PREFERENCE, limit=100)
    rels = await memory.get_memories(user_id, MemoryType.RELATIONSHIP, limit=100)

    return {
        "total_facts": len(facts),
        "total_preferences": len(prefs),
        "total_relationships": len(rels),
        "total_memories": len(facts) + len(prefs) + len(rels)
    }
