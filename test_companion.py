#!/usr/bin/env python3
"""Full companion test"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.personality.companion import Companion
from app.config import settings


async def test():
    print(f"\n{'='*50}")
    print(f"  Testing {settings.companion_name} Companion")
    print(f"{'='*50}\n")

    companion = Companion()
    user_id = "test-joe"

    # Test 1: Greeting
    print("1. Getting greeting...")
    greeting = await companion.get_greeting(user_id)
    print(f"   {settings.companion_name}: {greeting}\n")

    # Test 2: First message with personal info
    print("2. Sending message with personal info...")
    response, conv_id, memories = await companion.chat(
        user_id=user_id,
        message="Hey! My name is Joe and I love building AI apps. Coffee is my fuel!"
    )
    print(f"   {settings.companion_name}: {response}")
    print(f"   [Memories saved: {len(memories)}]\n")

    # Test 3: Follow-up question
    print("3. Testing memory recall...")
    response2, _, _ = await companion.chat(
        user_id=user_id,
        message="What do you know about me so far?",
        conversation_id=conv_id
    )
    print(f"   {settings.companion_name}: {response2}\n")

    # Test 4: Check stored memories
    print("4. Checking database memories...")
    stored = await companion.memory.get_memories(user_id, limit=5)
    print(f"   Found {len(stored)} memories in database:")
    for m in stored:
        print(f"   - [{m.memory_type.value}] {m.content}")

    print(f"\n{'='*50}")
    print("  All tests complete!")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    asyncio.run(test())
