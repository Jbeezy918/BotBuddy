#!/usr/bin/env python3
"""
BotBuddy - Terminal Chat Interface

100% FREE - Uses local Ollama models
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from app.personality.companion import Companion
from app.core.brain import get_brain
from app.config import settings


async def main():
    print(f"\n{'='*50}")
    print(f"  BotBuddy - {settings.companion_name}")
    print(f"  Powered by LOCAL models (100% free)")
    print(f"{'='*50}")

    # Check Ollama
    brain = get_brain()
    if await brain.check_ollama():
        models = await brain.list_models()
        print(f"  Ollama: ✓ ({len(models)} models)")
    else:
        print(f"  Ollama: ✗ (start with 'ollama serve')")
        print(f"  Will use Anthropic API as fallback")

    print(f"\n  Commands:")
    print(f"    quit     - Exit")
    print(f"    name X   - Rename your buddy")
    print(f"    memories - View stored memories")
    print(f"    models   - List available models")
    print(f"{'='*50}\n")

    companion = Companion()
    user_id = "terminal-user"
    conversation_id = None

    # Get initial greeting
    try:
        greeting = await companion.get_greeting(user_id)
        print(f"{settings.companion_name}: {greeting}\n")
    except Exception as e:
        print(f"{settings.companion_name}: Hi there! How are you doing?\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() == 'quit':
                print(f"\n{companion.name}: Take care! Talk soon.\n")
                break

            if user_input.lower().startswith('name '):
                new_name = user_input[5:].strip()
                await companion.set_companion_name(new_name)
                print(f"\n[Buddy renamed to {new_name}]\n")
                continue

            if user_input.lower() == 'memories':
                memories = await companion.memory.get_memories(user_id, limit=10)
                print(f"\n--- Memories ({len(memories)}) ---")
                for m in memories:
                    print(f"  [{m.memory_type.value}] {m.content}")
                print("---\n")
                continue

            if user_input.lower() == 'models':
                models = await brain.list_models()
                print(f"\n--- Available Models ---")
                for m in models:
                    print(f"  {m}")
                print("---\n")
                continue

            # Chat
            response, conversation_id, new_memories = await companion.chat(
                user_id=user_id,
                message=user_input,
                conversation_id=conversation_id
            )

            print(f"\n{companion.name}: {response}")

            if new_memories:
                print(f"  [+{len(new_memories)} memories saved]")
            print()

        except KeyboardInterrupt:
            print(f"\n\n{companion.name}: Goodbye!\n")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
