#!/usr/bin/env python3
"""Test the memory import system"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.importer import MemoryImporter
from app.importer.parsers import ChatGPTParser, detect_and_parse


# Sample ChatGPT export data
SAMPLE_CHATGPT_DATA = [
    {
        "id": "test-convo-1",
        "title": "Getting to know Joe",
        "create_time": 1700000000,
        "mapping": {
            "msg1": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"parts": ["Hi! My name is Joe and I'm a software developer. I love coffee and building AI apps."]},
                    "create_time": 1700000001
                }
            },
            "msg2": {
                "message": {
                    "author": {"role": "assistant"},
                    "content": {"parts": ["Nice to meet you Joe! What kind of AI apps are you working on?"]},
                    "create_time": 1700000002
                }
            },
            "msg3": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"parts": ["I'm building a companion app. My daughter Sarah, who is 10, gave me the idea. She said she wanted an AI friend."]},
                    "create_time": 1700000003
                }
            }
        }
    }
]


async def test_parser():
    """Test parsing"""
    print("1. Testing ChatGPT parser...")

    # Save sample data
    test_file = Path("/tmp/test_chatgpt_export.json")
    with open(test_file, 'w') as f:
        json.dump(SAMPLE_CHATGPT_DATA, f)

    conversations = ChatGPTParser.parse(str(test_file))
    print(f"   Parsed {len(conversations)} conversations")

    for conv in conversations:
        print(f"   - {conv.title}: {len(conv.messages)} messages")
        for msg in conv.messages:
            print(f"     [{msg.role}] {msg.content[:50]}...")

    return test_file


async def test_import(test_file):
    """Test full import"""
    print("\n2. Testing memory import...")

    importer = MemoryImporter("test-import-user")

    # Preview first
    print("   Getting preview...")
    preview = await importer.get_import_preview(str(test_file))
    print(f"   Preview: {preview}")

    # Do import
    print("   Running import...")
    result = await importer.import_from_file(str(test_file), "chatgpt")

    print(f"\n   Results:")
    print(f"   - Conversations processed: {result.conversations_processed}")
    print(f"   - Memories extracted: {result.memories_extracted}")
    print(f"   - Memories saved: {result.memories_saved}")

    if result.errors:
        print(f"   - Errors: {result.errors}")

    return result


async def verify_memories():
    """Verify memories were saved"""
    print("\n3. Verifying saved memories...")

    from app.memory import MemoryManager
    memory = MemoryManager()

    memories = await memory.get_memories("test-import-user", limit=20)
    print(f"   Found {len(memories)} memories:")

    for m in memories:
        print(f"   - [{m.memory_type.value}] {m.content}")


async def main():
    print("="*50)
    print("  Memory Import Test")
    print("="*50 + "\n")

    test_file = await test_parser()
    result = await test_import(test_file)
    await verify_memories()

    print("\n" + "="*50)
    if result.memories_saved > 0:
        print("  ✓ Import system working!")
    else:
        print("  ✗ No memories saved - check errors")
    print("="*50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
