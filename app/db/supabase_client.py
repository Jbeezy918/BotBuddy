"""
Supabase Client for BotBuddy
Handles all database operations
"""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from supabase import create_client, Client

# Initialize client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

_client: Optional[Client] = None

def get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# ==================== USERS ====================

async def get_or_create_user(user_id: str, username: str = None, email: str = None,
                              password_hash: str = None, buddy_name: str = "Buddy",
                              personality: str = "friendly", voice: str = "samantha") -> Dict:
    """Get existing user or create new one"""
    client = get_client()

    # Try to get existing user
    result = client.table("botbuddy_users").select("*").eq("user_id", user_id).execute()

    if result.data:
        return result.data[0]

    # Create new user
    new_user = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "buddy_name": buddy_name,
        "personality": personality,
        "voice": voice
    }
    result = client.table("botbuddy_users").insert(new_user).execute()

    # Update daily stats
    await increment_daily_stat("new_users")
    await increment_daily_stat("total_users")

    return result.data[0] if result.data else new_user


async def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email for login"""
    client = get_client()
    result = client.table("botbuddy_users").select("*").eq("email", email).execute()
    return result.data[0] if result.data else None


async def update_user(user_id: str, updates: Dict) -> Dict:
    """Update user profile"""
    client = get_client()
    updates["last_interaction"] = datetime.utcnow().isoformat()
    result = client.table("botbuddy_users").update(updates).eq("user_id", user_id).execute()
    return result.data[0] if result.data else {}


async def update_last_interaction(user_id: str):
    """Update last interaction timestamp"""
    client = get_client()
    client.table("botbuddy_users").update({
        "last_interaction": datetime.utcnow().isoformat()
    }).eq("user_id", user_id).execute()


# ==================== MEMORIES ====================

async def store_memory(user_id: str, content: str, memory_type: str = "fact",
                       importance: str = "medium", keywords: List[str] = None,
                       source: str = None) -> Dict:
    """Store a new memory"""
    client = get_client()

    memory = {
        "user_id": user_id,
        "content": content,
        "memory_type": memory_type,
        "importance": importance,
        "keywords": keywords or [],
        "source": source
    }
    result = client.table("botbuddy_memories").insert(memory).execute()

    # Update daily stats
    await increment_daily_stat("total_memories")

    return result.data[0] if result.data else memory


async def get_memories(user_id: str, memory_type: str = None, limit: int = 50) -> List[Dict]:
    """Get user's memories"""
    client = get_client()

    query = client.table("botbuddy_memories").select("*").eq("user_id", user_id)

    if memory_type:
        query = query.eq("memory_type", memory_type)

    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data or []


async def search_memories(user_id: str, search_query: str, limit: int = 10) -> List[Dict]:
    """Search memories by content"""
    client = get_client()

    # Simple text search (Supabase full-text search)
    result = client.table("botbuddy_memories").select("*").eq("user_id", user_id).ilike("content", f"%{search_query}%").limit(limit).execute()
    return result.data or []


# ==================== CONVERSATIONS ====================

async def start_conversation(user_id: str) -> Dict:
    """Start a new conversation"""
    client = get_client()

    convo = {
        "user_id": user_id,
        "message_count": 0
    }
    result = client.table("botbuddy_conversations").insert(convo).execute()
    return result.data[0] if result.data else convo


async def get_conversation(conversation_id: str) -> Optional[Dict]:
    """Get conversation by ID"""
    client = get_client()
    result = client.table("botbuddy_conversations").select("*").eq("id", conversation_id).execute()
    return result.data[0] if result.data else None


async def get_recent_conversations(user_id: str, limit: int = 10) -> List[Dict]:
    """Get recent conversations"""
    client = get_client()
    result = client.table("botbuddy_conversations").select("*").eq("user_id", user_id).order("started_at", desc=True).limit(limit).execute()
    return result.data or []


# ==================== MESSAGES ====================

async def add_message(conversation_id: str, user_id: str, role: str, content: str,
                      detected_mood: str = None) -> Dict:
    """Add a message to conversation"""
    client = get_client()

    message = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "detected_mood": detected_mood
    }
    result = client.table("botbuddy_messages").insert(message).execute()

    # Update conversation message count
    client.rpc("increment_message_count", {"conv_id": conversation_id}).execute()

    # Update daily stats
    await increment_daily_stat("total_messages")

    return result.data[0] if result.data else message


async def get_conversation_history(conversation_id: str, limit: int = 50) -> List[Dict]:
    """Get messages from a conversation"""
    client = get_client()
    result = client.table("botbuddy_messages").select("*").eq("conversation_id", conversation_id).order("created_at").limit(limit).execute()
    return result.data or []


# ==================== ANALYTICS ====================

async def track_event(event_type: str, metadata: Dict = None):
    """Track an analytics event"""
    client = get_client()

    event = {
        "event_type": event_type,
        "metadata": metadata or {}
    }
    client.table("botbuddy_analytics").insert(event).execute()


async def increment_daily_stat(stat_name: str, amount: int = 1):
    """Increment a daily stat"""
    client = get_client()
    today = date.today().isoformat()

    # Try to update existing row
    result = client.table("botbuddy_daily_stats").select("*").eq("date", today).execute()

    if result.data:
        current = result.data[0].get(stat_name, 0)
        client.table("botbuddy_daily_stats").update({
            stat_name: current + amount
        }).eq("date", today).execute()
    else:
        # Create new row for today
        client.table("botbuddy_daily_stats").insert({
            "date": today,
            stat_name: amount
        }).execute()


async def get_analytics_dashboard() -> Dict:
    """Get analytics data for dashboard"""
    client = get_client()

    # Get last 30 days stats
    stats = client.table("botbuddy_daily_stats").select("*").order("date", desc=True).limit(30).execute()

    # Get totals
    users = client.table("botbuddy_users").select("id", count="exact").execute()
    memories = client.table("botbuddy_memories").select("id", count="exact").execute()
    messages = client.table("botbuddy_messages").select("id", count="exact").execute()

    return {
        "total_users": users.count or 0,
        "total_memories": memories.count or 0,
        "total_messages": messages.count or 0,
        "daily_stats": stats.data or []
    }
