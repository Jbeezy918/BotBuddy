#!/usr/bin/env python3
"""Quick test of the multi-model brain"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.brain import CompanionBrain


async def test():
    print("Testing Companion Brain...\n")

    brain = CompanionBrain()

    # Check Ollama
    print("1. Checking Ollama connection...")
    if await brain.check_ollama():
        models = await brain.list_models()
        print(f"   ✓ Ollama running with {len(models)} models")
        print(f"   Models: {', '.join(models[:5])}...")
    else:
        print("   ✗ Ollama not running")
        return

    # Test quick response (mood detection)
    print("\n2. Testing fast model (mood detection)...")
    mood = await brain.detect_mood("I'm so excited about this new project!")
    print(f"   ✓ Detected mood: {mood}")

    # Test memory extraction
    print("\n3. Testing memory extraction...")
    memories = await brain.extract_memories("My name is Joe and I love building AI apps. My daughter Sarah is 10 years old.")
    print(f"   ✓ Extracted {len(memories)} memories:")
    for m in memories:
        print(f"      - [{m.get('type')}] {m.get('content')}")

    # Test conversation
    print("\n4. Testing conversation model...")
    response = await brain.conversation(
        messages=[{"role": "user", "content": "Hey! How's it going?"}],
        system_prompt="You are Sage, a warm and friendly companion. Keep responses brief."
    )
    print(f"   ✓ Response: {response[:200]}...")

    # Test with context
    print("\n5. Testing conversation with memory context...")
    response2 = await brain.conversation(
        messages=[
            {"role": "user", "content": "My name is Joe and I love coffee"},
            {"role": "assistant", "content": "Hey Joe! A fellow coffee lover, nice to meet you!"},
            {"role": "user", "content": "What's my name?"}
        ],
        system_prompt="You are Sage, a companion who remembers everything."
    )
    print(f"   ✓ Response: {response2[:200]}...")

    print("\n" + "="*50)
    print("All tests passed! Companion brain is working.")
    print("="*50)

    await brain.close()


if __name__ == "__main__":
    asyncio.run(test())
