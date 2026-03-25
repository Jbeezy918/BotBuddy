#!/usr/bin/env python3
"""
RoboBuddy - Terminal Chat Interface

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
from app.analytics import track_event, FeedbackCollector
from app.analytics.tracker import EventType, get_analytics
from app.analytics.feedback import FeedbackType


async def check_analytics_consent():
    """Check if user has made analytics choice, prompt if not"""
    analytics = get_analytics()
    consent_path = Path.home() / ".robobuddy" / "analytics_consent.json"

    if not consent_path.exists():
        print("\n" + "="*50)
        print("  Quick question about anonymous analytics:")
        print("="*50)
        print("\n  We'd love to know which features you use most")
        print("  so we can make RoboBuddy better.")
        print("\n  What we track (if you opt in):")
        print("    - Feature usage counts (e.g., 'chat used 50 times')")
        print("    - Success/failure rates")
        print("    - App version")
        print("\n  What we NEVER track:")
        print("    - Your conversations")
        print("    - Your memories")
        print("    - Your identity (no IDs, no IPs)")
        print("    - Any personal information")

        while True:
            choice = input("\n  Enable anonymous analytics? (y/n): ").strip().lower()
            if choice in ('y', 'yes'):
                analytics.opt_in()
                print("  ✓ Thanks! Analytics enabled.\n")
                await track_event(EventType.APP_STARTED)
                break
            elif choice in ('n', 'no'):
                analytics.opt_out()
                print("  ✓ No problem! Analytics disabled.\n")
                break
            else:
                print("  Please enter 'y' or 'n'")


async def main():
    print(f"\n{'='*50}")
    print(f"  RoboBuddy - {settings.companion_name}")
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

    # Check analytics consent (only asks once, ever)
    await check_analytics_consent()

    print(f"\n  Commands:")
    print(f"    quit     - Exit")
    print(f"    name X   - Rename your buddy")
    print(f"    memories - View stored memories")
    print(f"    models   - List available models")
    print(f"    feedback - Send us feedback")
    print(f"    privacy  - View/change analytics settings")
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

            if user_input.lower() == 'feedback':
                print("\n--- Send Feedback ---")
                print("  What would you like to tell us?")
                print("  (feature request, bug report, or general feedback)")
                feedback_msg = input("\n  Your feedback: ").strip()
                if feedback_msg:
                    collector = FeedbackCollector()
                    await collector.submit(FeedbackType.GENERAL, feedback_msg)
                    print("  ✓ Thanks for your feedback!\n")
                else:
                    print("  (cancelled)\n")
                continue

            if user_input.lower() == 'privacy':
                analytics = get_analytics()
                status = analytics.get_consent_status()
                print(f"\n--- Privacy Settings ---")
                print(f"  Analytics: {'Enabled' if status['enabled'] else 'Disabled'}")
                if status['enabled']:
                    print("\n  We track:")
                    for item in status['what_we_track']:
                        print(f"    - {item}")
                print("\n  Change setting? (on/off/cancel)")
                choice = input("  > ").strip().lower()
                if choice == 'on':
                    analytics.opt_in()
                    print("  ✓ Analytics enabled\n")
                elif choice == 'off':
                    analytics.opt_out()
                    print("  ✓ Analytics disabled\n")
                else:
                    print("  (no changes)\n")
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
            # Flush analytics on exit
            analytics = get_analytics()
            await analytics.flush()
            print(f"\n\n{companion.name}: Goodbye!\n")
            break
        except Exception as e:
            await track_event(EventType.ERROR_OCCURRED, success=False)
            print(f"\nError: {e}\n")

    # Final flush
    analytics = get_analytics()
    await analytics.flush()


if __name__ == "__main__":
    asyncio.run(main())
