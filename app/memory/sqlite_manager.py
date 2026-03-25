"""
SQLite Memory Manager - Fast, Free, Local

No external dependencies. Just works.
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from .models import Memory, MemoryType, MemoryImportance, UserProfile, Conversation, Message
from ..config import settings


class SQLiteMemoryManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.database_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database tables"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                phone_number TEXT UNIQUE,
                email TEXT,
                name TEXT,
                preferred_name TEXT,
                timezone TEXT DEFAULT 'America/Chicago',
                communication_style TEXT,
                humor_level TEXT,
                morning_checkin_enabled INTEGER DEFAULT 1,
                evening_checkin_enabled INTEGER DEFAULT 1,
                proactive_checkins_enabled INTEGER DEFAULT 1,
                total_conversations INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                first_interaction TEXT,
                last_interaction TEXT,
                current_mood TEXT,
                mood_updated_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance TEXT DEFAULT 'medium',
                keywords TEXT DEFAULT '[]',
                source_message_id TEXT,
                event_date TEXT,
                follow_up_date TEXT,
                reference_count INTEGER DEFAULT 0,
                last_referenced TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT,
                message_count INTEGER DEFAULT 0,
                summary TEXT,
                key_topics TEXT DEFAULT '[]',
                overall_mood TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                detected_mood TEXT,
                mood_confidence REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Indexes for speed
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(user_id, memory_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_followup ON memories(follow_up_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_convo ON messages(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)")

        conn.commit()
        conn.close()

    # ==================== USER METHODS ====================

    async def get_or_create_user(self, user_id: str) -> UserProfile:
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()

        if row:
            conn.close()
            return self._row_to_user(row)

        # Create new user
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT INTO users (id, first_interaction, created_at)
            VALUES (?, ?, ?)
        """, (user_id, now, now))
        conn.commit()
        conn.close()

        return UserProfile(id=user_id, first_interaction=datetime.utcnow())

    async def update_user(self, user: UserProfile) -> UserProfile:
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users SET
                phone_number = ?, email = ?, name = ?, preferred_name = ?,
                timezone = ?, communication_style = ?, humor_level = ?,
                morning_checkin_enabled = ?, evening_checkin_enabled = ?,
                proactive_checkins_enabled = ?, current_mood = ?, mood_updated_at = ?
            WHERE id = ?
        """, (
            user.phone_number, user.email, user.name, user.preferred_name,
            user.timezone, user.communication_style, user.humor_level,
            1 if user.morning_checkin_enabled else 0,
            1 if user.evening_checkin_enabled else 0,
            1 if user.proactive_checkins_enabled else 0,
            user.current_mood,
            user.mood_updated_at.isoformat() if user.mood_updated_at else None,
            user.id
        ))
        conn.commit()
        conn.close()
        return user

    async def update_last_interaction(self, user_id: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_interaction = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), user_id)
        )
        conn.commit()
        conn.close()

    def _row_to_user(self, row) -> UserProfile:
        return UserProfile(
            id=row["id"],
            phone_number=row["phone_number"],
            email=row["email"],
            name=row["name"],
            preferred_name=row["preferred_name"],
            timezone=row["timezone"] or "America/Chicago",
            communication_style=row["communication_style"],
            humor_level=row["humor_level"],
            morning_checkin_enabled=bool(row["morning_checkin_enabled"]),
            evening_checkin_enabled=bool(row["evening_checkin_enabled"]),
            proactive_checkins_enabled=bool(row["proactive_checkins_enabled"]),
            total_conversations=row["total_conversations"] or 0,
            total_messages=row["total_messages"] or 0,
            first_interaction=datetime.fromisoformat(row["first_interaction"]) if row["first_interaction"] else None,
            last_interaction=datetime.fromisoformat(row["last_interaction"]) if row["last_interaction"] else None,
            current_mood=row["current_mood"],
            mood_updated_at=datetime.fromisoformat(row["mood_updated_at"]) if row["mood_updated_at"] else None
        )

    # ==================== MEMORY METHODS ====================

    async def store_memory(self, memory: Memory) -> Memory:
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO memories (user_id, memory_type, content, importance, keywords,
                                  source_message_id, event_date, follow_up_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.user_id,
            memory.memory_type.value,
            memory.content,
            memory.importance.value,
            json.dumps(memory.keywords),
            memory.source_message_id,
            memory.event_date.isoformat() if memory.event_date else None,
            memory.follow_up_date.isoformat() if memory.follow_up_date else None,
            datetime.utcnow().isoformat()
        ))

        memory.id = str(cursor.lastrowid)
        conn.commit()
        conn.close()
        return memory

    async def get_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 50
    ) -> List[Memory]:
        conn = self._get_conn()
        cursor = conn.cursor()

        if memory_type:
            cursor.execute("""
                SELECT * FROM memories
                WHERE user_id = ? AND memory_type = ?
                ORDER BY
                    CASE importance
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        ELSE 4
                    END,
                    created_at DESC
                LIMIT ?
            """, (user_id, memory_type.value, limit))
        else:
            cursor.execute("""
                SELECT * FROM memories
                WHERE user_id = ?
                ORDER BY
                    CASE importance
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        ELSE 4
                    END,
                    created_at DESC
                LIMIT ?
            """, (user_id, limit))

        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_memory(r) for r in rows]

    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Memory]:
        """Keyword-based search with Claude relevance scoring"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Get all memories for user
        cursor.execute("""
            SELECT * FROM memories WHERE user_id = ?
            ORDER BY created_at DESC LIMIT 100
        """, (user_id,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        memories = [self._row_to_memory(r) for r in rows]

        # Quick keyword filter first
        query_words = set(query.lower().split())
        scored = []
        for m in memories:
            content_words = set(m.content.lower().split())
            keyword_set = set(k.lower() for k in m.keywords)
            overlap = len(query_words & (content_words | keyword_set))
            if overlap > 0 or any(qw in m.content.lower() for qw in query_words):
                scored.append((m, overlap))

        # Sort by overlap and return top matches
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:limit]]

    async def get_upcoming_followups(self, user_id: str) -> List[Memory]:
        conn = self._get_conn()
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()
        tomorrow = (datetime.utcnow() + timedelta(days=1)).isoformat()

        cursor.execute("""
            SELECT * FROM memories
            WHERE user_id = ? AND memory_type = 'episodic'
            AND follow_up_date IS NOT NULL
            AND follow_up_date >= ? AND follow_up_date <= ?
        """, (user_id, now, tomorrow))

        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_memory(r) for r in rows]

    def _row_to_memory(self, row) -> Memory:
        return Memory(
            id=str(row["id"]),
            user_id=row["user_id"],
            memory_type=MemoryType(row["memory_type"]),
            content=row["content"],
            importance=MemoryImportance(row["importance"]),
            keywords=json.loads(row["keywords"]) if row["keywords"] else [],
            source_message_id=row["source_message_id"],
            event_date=datetime.fromisoformat(row["event_date"]) if row["event_date"] else None,
            follow_up_date=datetime.fromisoformat(row["follow_up_date"]) if row["follow_up_date"] else None,
            reference_count=row["reference_count"] or 0,
            last_referenced=datetime.fromisoformat(row["last_referenced"]) if row["last_referenced"] else None,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow()
        )

    # ==================== CONVERSATION METHODS ====================

    async def start_conversation(self, user_id: str) -> Conversation:
        conn = self._get_conn()
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT INTO conversations (user_id, started_at)
            VALUES (?, ?)
        """, (user_id, now))

        convo_id = cursor.lastrowid

        # Update user stats
        cursor.execute("""
            UPDATE users SET total_conversations = total_conversations + 1
            WHERE id = ?
        """, (user_id,))

        conn.commit()
        conn.close()

        return Conversation(id=str(convo_id), user_id=user_id)

    async def add_message(self, message: Message) -> Message:
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO messages (conversation_id, user_id, role, content,
                                  detected_mood, mood_confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            message.conversation_id,
            message.user_id,
            message.role,
            message.content,
            message.detected_mood,
            message.mood_confidence,
            datetime.utcnow().isoformat()
        ))

        message.id = str(cursor.lastrowid)

        # Update counts
        cursor.execute("""
            UPDATE conversations SET message_count = message_count + 1
            WHERE id = ?
        """, (message.conversation_id,))

        cursor.execute("""
            UPDATE users SET total_messages = total_messages + 1
            WHERE id = ?
        """, (message.user_id,))

        conn.commit()
        conn.close()
        return message

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> List[Message]:
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            LIMIT ?
        """, (conversation_id, limit))

        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_message(r) for r in rows]

    async def get_recent_conversations(
        self,
        user_id: str,
        days: int = 7,
        limit: int = 10
    ) -> List[Conversation]:
        conn = self._get_conn()
        cursor = conn.cursor()

        since = (datetime.utcnow() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT * FROM conversations
            WHERE user_id = ? AND started_at >= ?
            ORDER BY started_at DESC
            LIMIT ?
        """, (user_id, since, limit))

        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_conversation(r) for r in rows]

    def _row_to_message(self, row) -> Message:
        return Message(
            id=str(row["id"]),
            conversation_id=str(row["conversation_id"]),
            user_id=row["user_id"],
            role=row["role"],
            content=row["content"],
            detected_mood=row["detected_mood"],
            mood_confidence=row["mood_confidence"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow()
        )

    def _row_to_conversation(self, row) -> Conversation:
        return Conversation(
            id=str(row["id"]),
            user_id=row["user_id"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else datetime.utcnow(),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            message_count=row["message_count"] or 0,
            summary=row["summary"],
            key_topics=json.loads(row["key_topics"]) if row["key_topics"] else [],
            overall_mood=row["overall_mood"]
        )

    # Note: Memory extraction moved to app/core/brain.py (uses local models)

    # ==================== CONTEXT BUILDING ====================

    async def build_memory_context(self, user_id: str, current_message: str) -> str:
        """Build context string for AI"""

        facts = await self.get_memories(user_id, MemoryType.FACT, limit=15)
        relationships = await self.get_memories(user_id, MemoryType.RELATIONSHIP, limit=10)
        relevant = await self.search_memories(user_id, current_message, limit=8)
        followups = await self.get_upcoming_followups(user_id)

        parts = []

        if facts:
            parts.append("**About you:**")
            for f in facts[:10]:
                parts.append(f"- {f.content}")

        if relationships:
            parts.append("\n**People in your life:**")
            for r in relationships[:5]:
                parts.append(f"- {r.content}")

        if relevant:
            parts.append("\n**Relevant memories:**")
            for r in relevant[:5]:
                parts.append(f"- {r.content}")

        if followups:
            parts.append("\n**To follow up on:**")
            for f in followups[:3]:
                parts.append(f"- {f.content}")

        return "\n".join(parts) if parts else ""

    # ==================== ADMIN METHODS ====================

    async def get_all_users_for_checkin(self, checkin_type: str) -> List[UserProfile]:
        """Get users who should receive check-ins"""
        conn = self._get_conn()
        cursor = conn.cursor()

        if checkin_type == "morning":
            cursor.execute("SELECT * FROM users WHERE morning_checkin_enabled = 1")
        elif checkin_type == "evening":
            cursor.execute("SELECT * FROM users WHERE evening_checkin_enabled = 1")
        else:
            cursor.execute("SELECT * FROM users WHERE proactive_checkins_enabled = 1")

        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_user(r) for r in rows]

    async def get_inactive_users(self, hours: int = 24) -> List[UserProfile]:
        """Get users who haven't interacted recently"""
        conn = self._get_conn()
        cursor = conn.cursor()

        threshold = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT * FROM users
            WHERE proactive_checkins_enabled = 1
            AND (last_interaction IS NULL OR last_interaction < ?)
        """, (threshold,))

        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_user(r) for r in rows]
