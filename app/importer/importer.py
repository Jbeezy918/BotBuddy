"""
Memory Importer

Takes parsed conversations from other AIs and extracts memories
to pre-populate the Companion's knowledge about the user.
"""
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from .parsers import (
    ParsedConversation,
    ParsedMessage,
    ChatGPTParser,
    ClaudeParser,
    GeminiParser,
    PerplexityParser,
    detect_and_parse
)
from ..core.brain import get_brain
from ..memory import MemoryManager
from ..memory.models import Memory, MemoryType, MemoryImportance


@dataclass
class ImportResult:
    """Result of a memory import"""
    source: str
    conversations_processed: int
    memories_extracted: int
    memories_saved: int
    errors: List[str]


class MemoryImporter:
    """
    Import memories from other AI platforms.

    Parses export files, extracts user information,
    and saves to Companion's memory system.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.brain = get_brain()
        self.memory = MemoryManager()

    async def import_from_file(
        self,
        file_path: str,
        source: str = "auto"
    ) -> ImportResult:
        """
        Import memories from an export file.

        Args:
            file_path: Path to export file (ZIP or JSON)
            source: "chatgpt", "claude", "gemini", "perplexity", or "auto"

        Returns:
            ImportResult with stats
        """
        errors = []

        # Parse the file
        if source == "auto":
            conversations = detect_and_parse(file_path)
        elif source == "chatgpt":
            conversations = ChatGPTParser.parse(file_path)
        elif source == "claude":
            conversations = ClaudeParser.parse(file_path)
        elif source == "gemini":
            conversations = GeminiParser.parse(file_path)
        elif source == "perplexity":
            conversations = PerplexityParser.parse(file_path)
        else:
            return ImportResult(
                source=source,
                conversations_processed=0,
                memories_extracted=0,
                memories_saved=0,
                errors=[f"Unknown source: {source}"]
            )

        if not conversations:
            return ImportResult(
                source=source,
                conversations_processed=0,
                memories_extracted=0,
                memories_saved=0,
                errors=["No conversations found in export file"]
            )

        # Extract memories from conversations
        all_memories = []
        for conv in conversations:
            try:
                memories = await self._extract_memories_from_conversation(conv)
                all_memories.extend(memories)
            except Exception as e:
                errors.append(f"Error processing conversation {conv.id}: {e}")

        # Deduplicate memories
        unique_memories = self._deduplicate_memories(all_memories)

        # Save to database
        saved_count = 0
        for mem_data in unique_memories:
            try:
                memory = Memory(
                    user_id=self.user_id,
                    memory_type=MemoryType(mem_data.get("type", "fact")),
                    content=mem_data.get("content", ""),
                    importance=MemoryImportance(mem_data.get("importance", "medium")),
                    keywords=mem_data.get("keywords", [])
                )
                await self.memory.store_memory(memory)
                saved_count += 1
            except Exception as e:
                errors.append(f"Error saving memory: {e}")

        return ImportResult(
            source=conversations[0].source if conversations else source,
            conversations_processed=len(conversations),
            memories_extracted=len(all_memories),
            memories_saved=saved_count,
            errors=errors
        )

    async def _extract_memories_from_conversation(
        self,
        conversation: ParsedConversation
    ) -> List[Dict]:
        """Extract memories from a single conversation"""
        memories = []

        # Get all user messages
        user_messages = [m.content for m in conversation.messages if m.role == "user"]

        if not user_messages:
            return []

        # Batch process user messages (to save API calls)
        # Combine messages and extract facts
        batch_size = 10
        for i in range(0, len(user_messages), batch_size):
            batch = user_messages[i:i + batch_size]
            combined = "\n---\n".join(batch)

            # Use brain to extract memories
            extracted = await self.brain.extract_memories(combined)
            memories.extend(extracted)

        return memories

    def _deduplicate_memories(self, memories: List[Dict]) -> List[Dict]:
        """Remove duplicate memories based on content similarity"""
        seen = set()
        unique = []

        for mem in memories:
            content = mem.get("content", "").lower().strip()

            # Simple dedup - check if content is too similar
            content_key = content[:50]  # First 50 chars as key

            if content_key not in seen and len(content) > 5:
                seen.add(content_key)
                unique.append(mem)

        return unique

    async def import_from_text(self, text: str) -> ImportResult:
        """
        Import memories from raw text (like copy-pasted conversations).
        """
        # Treat as a single conversation
        memories = await self.brain.extract_memories(text)

        saved_count = 0
        errors = []

        for mem_data in memories:
            try:
                memory = Memory(
                    user_id=self.user_id,
                    memory_type=MemoryType(mem_data.get("type", "fact")),
                    content=mem_data.get("content", ""),
                    importance=MemoryImportance(mem_data.get("importance", "medium")),
                    keywords=mem_data.get("keywords", [])
                )
                await self.memory.store_memory(memory)
                saved_count += 1
            except Exception as e:
                errors.append(str(e))

        return ImportResult(
            source="text",
            conversations_processed=1,
            memories_extracted=len(memories),
            memories_saved=saved_count,
            errors=errors
        )

    async def get_import_preview(
        self,
        file_path: str,
        source: str = "auto"
    ) -> Dict[str, Any]:
        """
        Preview what would be imported without saving.

        Returns stats and sample memories.
        """
        # Parse file
        if source == "auto":
            conversations = detect_and_parse(file_path)
        elif source == "chatgpt":
            conversations = ChatGPTParser.parse(file_path)
        elif source == "claude":
            conversations = ClaudeParser.parse(file_path)
        elif source == "gemini":
            conversations = GeminiParser.parse(file_path)
        else:
            return {"error": f"Unknown source: {source}"}

        if not conversations:
            return {"error": "No conversations found"}

        # Sample extraction (first 3 conversations)
        sample_memories = []
        for conv in conversations[:3]:
            try:
                memories = await self._extract_memories_from_conversation(conv)
                sample_memories.extend(memories[:5])
            except:
                continue

        # Count user messages
        total_user_messages = sum(
            len([m for m in c.messages if m.role == "user"])
            for c in conversations
        )

        return {
            "source": conversations[0].source if conversations else source,
            "total_conversations": len(conversations),
            "total_user_messages": total_user_messages,
            "sample_memories": sample_memories[:10],
            "estimated_memories": len(sample_memories) * (len(conversations) // 3 + 1)
        }
