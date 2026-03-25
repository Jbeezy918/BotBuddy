"""
Memory Data Models
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MemoryType(str, Enum):
    FACT = "fact"           # Static info: name, age, job, family
    EPISODIC = "episodic"   # Specific events: "doctor appointment Tuesday"
    EMOTIONAL = "emotional"  # Mood patterns: "sad on Mondays", "anxious about work"
    PREFERENCE = "preference"  # Likes/dislikes: "loves coffee", "hates mornings"
    RELATIONSHIP = "relationship"  # People in their life: "daughter Sarah", "friend Mike"


class MemoryImportance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"  # Never forget


class Memory(BaseModel):
    id: Optional[str] = None
    user_id: str
    memory_type: MemoryType
    content: str
    importance: MemoryImportance = MemoryImportance.MEDIUM
    keywords: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_referenced: Optional[datetime] = None
    reference_count: int = 0
    source_message_id: Optional[str] = None

    # For episodic memories
    event_date: Optional[datetime] = None
    follow_up_date: Optional[datetime] = None  # When to ask about this


class UserProfile(BaseModel):
    id: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    preferred_name: Optional[str] = None
    timezone: str = "America/Chicago"

    # Personality insights
    communication_style: Optional[str] = None  # "brief", "detailed", "emotional"
    humor_level: Optional[str] = None  # "dry", "playful", "minimal"

    # Check-in preferences
    morning_checkin_enabled: bool = True
    evening_checkin_enabled: bool = True
    proactive_checkins_enabled: bool = True

    # Stats
    total_conversations: int = 0
    total_messages: int = 0
    first_interaction: Optional[datetime] = None
    last_interaction: Optional[datetime] = None

    # Current state
    current_mood: Optional[str] = None
    mood_updated_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class Message(BaseModel):
    id: Optional[str] = None
    conversation_id: str
    user_id: str
    role: str  # "user" or "assistant"
    content: str
    detected_mood: Optional[str] = None
    mood_confidence: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    id: Optional[str] = None
    user_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    message_count: int = 0
    summary: Optional[str] = None
    key_topics: List[str] = Field(default_factory=list)
    overall_mood: Optional[str] = None
    memories_created: List[str] = Field(default_factory=list)
