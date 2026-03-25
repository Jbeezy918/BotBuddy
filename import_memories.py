#!/usr/bin/env python3
"""
Memory Import CLI

Import your chat history from ChatGPT, Claude, Gemini, and more.
Your new Companion will know you from day one.

Usage:
    python import_memories.py <export_file> [--source chatgpt|claude|gemini|auto]

Examples:
    python import_memories.py ~/Downloads/chatgpt_export.zip
    python import_memories.py ~/Downloads/claude_export.json --source claude
    python import_memories.py ~/Downloads/conversations.json --preview
"""
import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.importer import MemoryImporter
from app.config import settings


async def main():
    parser = argparse.ArgumentParser(
        description="Import memories from other AI platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python import_memories.py chatgpt_export.zip
  python import_memories.py claude_export.json --source claude
  python import_memories.py export.json --preview

Supported formats:
  - ChatGPT: ZIP export from Settings > Data Controls > Export
  - Claude: JSON export from claude.ai
  - Gemini: Google Takeout export
  - Perplexity: JSON export
        """
    )

    parser.add_argument("file", help="Path to export file (ZIP or JSON)")
    parser.add_argument(
        "--source", "-s",
        choices=["auto", "chatgpt", "claude", "gemini", "perplexity"],
        default="auto",
        help="Source platform (default: auto-detect)"
    )
    parser.add_argument(
        "--preview", "-p",
        action="store_true",
        help="Preview what would be imported without saving"
    )
    parser.add_argument(
        "--user", "-u",
        default="default-user",
        help="User ID for the import (default: default-user)"
    )

    args = parser.parse_args()

    # Check file exists
    file_path = Path(args.file).expanduser()
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"  {settings.companion_name} - Memory Import")
    print(f"{'='*50}")
    print(f"  File: {file_path.name}")
    print(f"  Source: {args.source}")
    print(f"  User: {args.user}")
    print(f"{'='*50}\n")

    importer = MemoryImporter(args.user)

    if args.preview:
        # Preview mode
        print("Analyzing export file...\n")
        preview = await importer.get_import_preview(str(file_path), args.source)

        if "error" in preview:
            print(f"Error: {preview['error']}")
            sys.exit(1)

        print(f"Source: {preview['source']}")
        print(f"Conversations: {preview['total_conversations']}")
        print(f"User messages: {preview['total_user_messages']}")
        print(f"Estimated memories: ~{preview['estimated_memories']}")

        if preview['sample_memories']:
            print(f"\nSample memories that would be extracted:")
            for mem in preview['sample_memories'][:5]:
                print(f"  - [{mem.get('type', 'fact')}] {mem.get('content', '')[:60]}...")

        print(f"\nRun without --preview to import these memories.")

    else:
        # Import mode
        print("Importing memories...\n")

        result = await importer.import_from_file(str(file_path), args.source)

        print(f"\n{'='*50}")
        print(f"  Import Complete!")
        print(f"{'='*50}")
        print(f"  Source: {result.source}")
        print(f"  Conversations processed: {result.conversations_processed}")
        print(f"  Memories extracted: {result.memories_extracted}")
        print(f"  Memories saved: {result.memories_saved}")

        if result.errors:
            print(f"\n  Errors ({len(result.errors)}):")
            for err in result.errors[:5]:
                print(f"    - {err}")

        print(f"\n{settings.companion_name} now knows you! Start chatting:")
        print(f"  python chat.py")
        print()


if __name__ == "__main__":
    asyncio.run(main())
