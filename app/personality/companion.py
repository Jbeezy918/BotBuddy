"""
The Companion - Main conversation handler

Uses multi-model brain for 100% free local inference.
Falls back to Anthropic if configured.
"""
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

from ..config import settings
from ..memory import MemoryManager
from ..memory.models import UserProfile, Conversation, Message, Memory, MemoryType, MemoryImportance
from ..core.brain import get_brain
from .prompts import SYSTEM_PROMPT, get_time_context


class Companion:
    def __init__(self):
        self.brain = get_brain()
        self.memory = MemoryManager()
        self.name = settings.companion_name

    async def chat(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        detected_mood: Optional[str] = None,
        mood_confidence: Optional[float] = None
    ) -> Tuple[str, str, List[Memory]]:
        """Main chat - returns (response, conversation_id, new_memories)"""

        # Get or create user
        user = await self.memory.get_or_create_user(user_id)

        # Start or continue conversation
        if not conversation_id:
            convo = await self.memory.start_conversation(user_id)
            conversation_id = convo.id

        # Store user message
        user_message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=message,
            detected_mood=detected_mood,
            mood_confidence=mood_confidence
        )
        await self.memory.add_message(user_message)

        # Build context
        memory_context = await self.memory.build_memory_context(user_id, message)
        time_context = get_time_context(user.timezone)

        # Auto-detect mood if not provided
        if not detected_mood:
            mood_data = await self.brain.detect_mood(message)
            detected_mood = mood_data.get("mood")
            mood_confidence = mood_data.get("confidence", 0.5)

        # System prompt with personality
        system_prompt = SYSTEM_PROMPT.format(
            name=self.name,
            time_context=time_context,
            memory_context=memory_context or "This is a new friend - you're just getting to know them."
        )

        if detected_mood and mood_confidence and mood_confidence > 0.5:
            system_prompt += f"\n\n**Note**: User seems {detected_mood}. Adjust your tone accordingly."

        # Get conversation history
        history = await self.memory.get_conversation_history(conversation_id, limit=15)

        # Build messages
        messages = [{"role": m.role, "content": m.content} for m in history]
        if not history or history[-1].content != message:
            messages.append({"role": "user", "content": message})

        # Get response from brain (local models first, Anthropic fallback)
        assistant_response = await self.brain.conversation(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.8
        )

        # Store assistant response
        await self.memory.add_message(Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=assistant_response
        ))

        # Extract memories using fast model
        memories_data = await self.brain.extract_memories(message)
        new_memories = []

        for m in memories_data:
            try:
                memory = Memory(
                    user_id=user_id,
                    memory_type=MemoryType(m.get("type", "fact")),
                    content=m.get("content", ""),
                    importance=MemoryImportance(m.get("importance", "medium")),
                    keywords=m.get("keywords", []),
                    source_message_id=conversation_id
                )
                stored = await self.memory.store_memory(memory)
                new_memories.append(stored)
            except Exception as e:
                print(f"Memory storage error: {e}")

        # Update last interaction
        await self.memory.update_last_interaction(user_id)

        return assistant_response, conversation_id, new_memories

    async def get_greeting(self, user_id: str) -> str:
        """Get personalized greeting"""
        user = await self.memory.get_or_create_user(user_id)
        time_context = get_time_context(user.timezone)
        followups = await self.memory.get_upcoming_followups(user_id)

        name = user.preferred_name or user.name or "friend"

        prompt = f"""Generate a warm, brief greeting for {name}.
Time: {time_context}
Last talked: {user.last_interaction.strftime("%A") if user.last_interaction else "never - new friend!"}
"""
        if followups:
            prompt += f"\nMaybe ask about: {followups[0].content}"

        prompt += "\n\n1-2 sentences max. Be natural and warm."

        response = await self.brain.conversation(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=f"You are {self.name}, a warm companion. Generate a greeting.",
            temperature=0.9
        )

        return response

    async def generate_proactive_message(self, user_id: str, message_type: str = "checkin") -> str:
        """Generate proactive check-in"""
        user = await self.memory.get_or_create_user(user_id)
        time_context = get_time_context(user.timezone)
        followups = await self.memory.get_upcoming_followups(user_id)

        name = user.preferred_name or user.name or "friend"

        prompt = f"""Generate a caring check-in message for {name}.
Type: {message_type}
Time: {time_context}
"""
        if followups:
            prompt += f"\nCould ask about: {followups[0].content}"

        prompt += "\n\n1-2 sentences. Warm but not clingy."

        response = await self.brain.conversation(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=f"You are {self.name} sending a check-in text.",
            temperature=0.9
        )

        return response

    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> UserProfile:
        """Update user profile"""
        user = await self.memory.get_or_create_user(user_id)
        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)
        return await self.memory.update_user(user)

    async def set_companion_name(self, new_name: str):
        """Change companion's name"""
        self.name = new_name
