"""
API Routes - RoboBuddy
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import hashlib

from ..config import settings
from ..personality.companion import Companion
from ..memory import MemoryManager
from ..analytics import Analytics, track_event, FeedbackCollector
from ..analytics.tracker import EventType, get_analytics
from ..analytics.feedback import FeedbackType

# Supabase client (if configured)
try:
    from ..db import supabase_client as db
    USE_SUPABASE = bool(settings.supabase_url and settings.supabase_key)
except ImportError:
    USE_SUPABASE = False
    db = None

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
    personality: Optional[str] = "friendly"
    reply_length: Optional[str] = "short"  # 'short' or 'long'


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


# ==================== AUTH ====================

class RegisterRequest(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None
    password: Optional[str] = None
    buddy_name: str = "Buddy"
    personality: str = "friendly"
    voice: str = "samantha"


class LoginRequest(BaseModel):
    email: str
    password: str


def hash_password(password: str) -> str:
    """Simple SHA256 hash for password"""
    return hashlib.sha256(password.encode()).hexdigest()


@router.post("/auth/register")
async def register_user(request: RegisterRequest):
    """Register a new user (or update existing guest to full account)"""
    if not USE_SUPABASE:
        # Fallback to local storage - just return success
        return {"success": True, "user_id": request.user_id, "message": "Guest mode (no database)"}

    try:
        password_hash = hash_password(request.password) if request.password else None

        user = await db.get_or_create_user(
            user_id=request.user_id,
            username=request.username,
            email=request.email,
            password_hash=password_hash,
            buddy_name=request.buddy_name,
            personality=request.personality,
            voice=request.voice
        )

        return {
            "success": True,
            "user_id": user.get("user_id"),
            "username": user.get("username"),
            "buddy_name": user.get("buddy_name"),
            "personality": user.get("personality"),
            "voice": user.get("voice")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/login")
async def login_user(request: LoginRequest):
    """Login with email and password"""
    if not USE_SUPABASE:
        raise HTTPException(status_code=400, detail="Database not configured")

    try:
        user = await db.get_user_by_email(request.email)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        if user.get("password_hash") != hash_password(request.password):
            raise HTTPException(status_code=401, detail="Invalid password")

        return {
            "success": True,
            "user_id": user.get("user_id"),
            "username": user.get("username"),
            "buddy_name": user.get("buddy_name"),
            "personality": user.get("personality"),
            "voice": user.get("voice")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            mood_confidence=request.mood_confidence,
            personality=request.personality,
            reply_length=request.reply_length
        )

        # Track anonymous usage (no content, just that chat was used)
        await track_event(EventType.CHAT_MESSAGE, success=True)
        if new_memories:
            await track_event(EventType.MEMORY_CREATED, metadata={"count": len(new_memories)})

        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            memories_created=len(new_memories)
        )
    except Exception as e:
        await track_event(EventType.ERROR_OCCURRED, success=False, metadata={"error_type": "chat"})
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


class SaveMemoryRequest(BaseModel):
    user_id: str
    content: str
    type: Optional[str] = "fact"


@router.post("/memories")
async def save_memory(request: SaveMemoryRequest):
    """Manually save a memory/key point"""
    from ..memory.models import Memory, MemoryType, MemoryImportance

    try:
        mem_type = MemoryType(request.type) if request.type else MemoryType.FACT
    except ValueError:
        mem_type = MemoryType.FACT

    new_memory = Memory(
        user_id=request.user_id,
        memory_type=mem_type,
        content=request.content,
        importance=MemoryImportance.HIGH,
        keywords=[],
        source_message_id="manual"
    )
    stored = await memory.store_memory(new_memory)
    return stored.model_dump()


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


# ==================== ANALYTICS (Anonymous, Opt-in) ====================

@router.get("/analytics/status")
async def get_analytics_status():
    """Get current analytics consent status and what we track"""
    analytics = get_analytics()
    return analytics.get_consent_status()


@router.post("/analytics/opt-in")
async def analytics_opt_in():
    """Opt into anonymous analytics"""
    analytics = get_analytics()
    analytics.opt_in()
    await track_event(EventType.APP_STARTED)  # Track first event
    return {"status": "opted_in", "message": "Thanks! We only track feature usage, never personal data."}


@router.post("/analytics/opt-out")
async def analytics_opt_out():
    """Opt out of analytics"""
    analytics = get_analytics()
    analytics.opt_out()
    return {"status": "opted_out", "message": "Analytics disabled. No data will be collected."}


# ==================== FEEDBACK (Voluntary) ====================

class FeedbackRequest(BaseModel):
    feedback_type: str  # feature_request, bug_report, general, like, improvement
    message: str
    feature_context: Optional[str] = None


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit voluntary feedback"""
    try:
        feedback_type = FeedbackType(request.feedback_type)
    except ValueError:
        feedback_type = FeedbackType.GENERAL

    collector = FeedbackCollector()
    success = await collector.submit(
        feedback_type=feedback_type,
        message=request.message,
        feature_context=request.feature_context
    )

    await track_event(EventType.FEEDBACK_SENT)

    return {
        "status": "received" if success else "queued",
        "message": "Thanks for your feedback!"
    }


@router.get("/feedback/pending")
async def get_pending_feedback():
    """Check if there's pending feedback that hasn't been sent"""
    collector = FeedbackCollector()
    return {"pending_count": collector.get_pending_count()}


# ==================== DASHBOARD (Admin) ====================

@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get analytics dashboard data"""
    if not USE_SUPABASE:
        return {
            "total_users": 0,
            "total_memories": 0,
            "total_messages": 0,
            "daily_stats": [],
            "message": "Database not configured - using local storage"
        }

    try:
        stats = await db.get_analytics_dashboard()
        return stats
    except Exception as e:
        return {
            "total_users": 0,
            "total_memories": 0,
            "total_messages": 0,
            "daily_stats": [],
            "error": str(e)
        }
