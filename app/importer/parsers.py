"""
Export Parsers for ChatGPT, Claude, Gemini

Parses exported data from other AI platforms and extracts
conversations that can be mined for memories.
"""
import json
import zipfile
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ParsedMessage:
    """A single message from an export"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None


@dataclass
class ParsedConversation:
    """A conversation from an export"""
    id: str
    title: Optional[str]
    messages: List[ParsedMessage]
    created_at: Optional[datetime] = None
    source: str = "unknown"


class ChatGPTParser:
    """
    Parse ChatGPT exports

    ChatGPT exports as a ZIP containing conversations.json
    Format: List of conversations, each with "mapping" containing messages
    """

    @staticmethod
    def parse(file_path: str) -> List[ParsedConversation]:
        """Parse ChatGPT export file (ZIP or JSON)"""
        conversations = []

        path = Path(file_path)

        # Handle ZIP file
        if path.suffix.lower() == '.zip':
            with zipfile.ZipFile(file_path, 'r') as zf:
                # Look for conversations.json
                for name in zf.namelist():
                    if 'conversations.json' in name:
                        with zf.open(name) as f:
                            data = json.load(f)
                            conversations = ChatGPTParser._parse_conversations(data)
                            break

        # Handle JSON file directly
        elif path.suffix.lower() == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                conversations = ChatGPTParser._parse_conversations(data)

        return conversations

    @staticmethod
    def _parse_conversations(data: List[Dict]) -> List[ParsedConversation]:
        """Parse the conversations.json format"""
        conversations = []

        for conv in data:
            try:
                conv_id = conv.get('id', str(len(conversations)))
                title = conv.get('title', 'Untitled')
                created = conv.get('create_time')

                messages = []
                mapping = conv.get('mapping', {})

                # Extract messages from mapping
                for node_id, node in mapping.items():
                    msg = node.get('message')
                    if not msg:
                        continue

                    author = msg.get('author', {}).get('role', '')
                    content_parts = msg.get('content', {}).get('parts', [])

                    if author in ['user', 'assistant'] and content_parts:
                        content = ' '.join(str(p) for p in content_parts if isinstance(p, str))
                        if content.strip():
                            messages.append(ParsedMessage(
                                role=author,
                                content=content,
                                timestamp=datetime.fromtimestamp(msg.get('create_time', 0)) if msg.get('create_time') else None
                            ))

                if messages:
                    conversations.append(ParsedConversation(
                        id=conv_id,
                        title=title,
                        messages=messages,
                        created_at=datetime.fromtimestamp(created) if created else None,
                        source="chatgpt"
                    ))

            except Exception as e:
                print(f"Error parsing conversation: {e}")
                continue

        return conversations


class ClaudeParser:
    """
    Parse Claude exports

    Claude exports as JSON with conversation history
    """

    @staticmethod
    def parse(file_path: str) -> List[ParsedConversation]:
        """Parse Claude export file"""
        conversations = []

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Claude export format varies - handle multiple formats
        if isinstance(data, list):
            # List of conversations
            for i, conv in enumerate(data):
                parsed = ClaudeParser._parse_single_conversation(conv, i)
                if parsed:
                    conversations.append(parsed)

        elif isinstance(data, dict):
            # Single conversation or wrapped format
            if 'conversations' in data:
                for i, conv in enumerate(data['conversations']):
                    parsed = ClaudeParser._parse_single_conversation(conv, i)
                    if parsed:
                        conversations.append(parsed)
            else:
                parsed = ClaudeParser._parse_single_conversation(data, 0)
                if parsed:
                    conversations.append(parsed)

        return conversations

    @staticmethod
    def _parse_single_conversation(conv: Dict, index: int) -> Optional[ParsedConversation]:
        """Parse a single Claude conversation"""
        try:
            messages = []

            # Handle different message formats
            msg_list = conv.get('chat_messages', conv.get('messages', []))

            for msg in msg_list:
                role = msg.get('sender', msg.get('role', ''))
                if role == 'human':
                    role = 'user'
                elif role == 'assistant' or role == 'claude':
                    role = 'assistant'
                else:
                    continue

                content = msg.get('text', msg.get('content', ''))
                if isinstance(content, list):
                    content = ' '.join(str(c.get('text', c)) for c in content if isinstance(c, dict))

                if content and content.strip():
                    messages.append(ParsedMessage(
                        role=role,
                        content=content.strip()
                    ))

            if messages:
                return ParsedConversation(
                    id=conv.get('uuid', str(index)),
                    title=conv.get('name', conv.get('title', 'Claude Chat')),
                    messages=messages,
                    created_at=None,
                    source="claude"
                )

        except Exception as e:
            print(f"Error parsing Claude conversation: {e}")

        return None


class GeminiParser:
    """
    Parse Google Gemini/Bard exports

    Gemini exports via Google Takeout as JSON
    """

    @staticmethod
    def parse(file_path: str) -> List[ParsedConversation]:
        """Parse Gemini export file"""
        conversations = []

        path = Path(file_path)

        # Handle directory (Takeout export)
        if path.is_dir():
            for json_file in path.glob('**/*.json'):
                convs = GeminiParser._parse_file(str(json_file))
                conversations.extend(convs)

        # Handle single JSON file
        elif path.suffix.lower() == '.json':
            conversations = GeminiParser._parse_file(file_path)

        # Handle ZIP
        elif path.suffix.lower() == '.zip':
            with zipfile.ZipFile(file_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.json'):
                        with zf.open(name) as f:
                            try:
                                data = json.load(f)
                                convs = GeminiParser._parse_data(data)
                                conversations.extend(convs)
                            except:
                                continue

        return conversations

    @staticmethod
    def _parse_file(file_path: str) -> List[ParsedConversation]:
        """Parse a single Gemini JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return GeminiParser._parse_data(data)
        except Exception as e:
            print(f"Error parsing Gemini file {file_path}: {e}")
            return []

    @staticmethod
    def _parse_data(data: Any) -> List[ParsedConversation]:
        """Parse Gemini data structure"""
        conversations = []

        # Gemini format varies - try multiple approaches
        if isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    conv = GeminiParser._extract_conversation(item, i)
                    if conv:
                        conversations.append(conv)

        elif isinstance(data, dict):
            conv = GeminiParser._extract_conversation(data, 0)
            if conv:
                conversations.append(conv)

        return conversations

    @staticmethod
    def _extract_conversation(data: Dict, index: int) -> Optional[ParsedConversation]:
        """Extract a conversation from Gemini data"""
        messages = []

        # Try different Gemini formats
        for key in ['textInput', 'userInput', 'prompt']:
            if key in data:
                messages.append(ParsedMessage(role='user', content=str(data[key])))

        for key in ['textOutput', 'response', 'modelResponse', 'output']:
            if key in data:
                content = data[key]
                if isinstance(content, list):
                    content = ' '.join(str(c) for c in content)
                messages.append(ParsedMessage(role='assistant', content=str(content)))

        # Handle nested conversation format
        if 'messages' in data or 'turns' in data:
            msg_list = data.get('messages', data.get('turns', []))
            for msg in msg_list:
                role = 'user' if msg.get('isUser', msg.get('role') == 'user') else 'assistant'
                content = msg.get('text', msg.get('content', ''))
                if content:
                    messages.append(ParsedMessage(role=role, content=str(content)))

        if messages:
            return ParsedConversation(
                id=str(index),
                title=data.get('title', 'Gemini Chat'),
                messages=messages,
                source="gemini"
            )

        return None


class PerplexityParser:
    """
    Parse Perplexity exports
    """

    @staticmethod
    def parse(file_path: str) -> List[ParsedConversation]:
        """Parse Perplexity export"""
        conversations = []

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            for i, conv in enumerate(data):
                messages = []

                for msg in conv.get('messages', conv.get('entries', [])):
                    role = msg.get('role', msg.get('author', ''))
                    if role in ['user', 'human']:
                        role = 'user'
                    elif role in ['assistant', 'ai', 'perplexity']:
                        role = 'assistant'
                    else:
                        continue

                    content = msg.get('content', msg.get('text', ''))
                    if content:
                        messages.append(ParsedMessage(role=role, content=content))

                if messages:
                    conversations.append(ParsedConversation(
                        id=str(i),
                        title=conv.get('title', 'Perplexity Search'),
                        messages=messages,
                        source="perplexity"
                    ))

        return conversations


def detect_and_parse(file_path: str) -> List[ParsedConversation]:
    """Auto-detect export format and parse"""
    path = Path(file_path)

    # Try each parser
    parsers = [
        ("ChatGPT", ChatGPTParser.parse),
        ("Claude", ClaudeParser.parse),
        ("Gemini", GeminiParser.parse),
        ("Perplexity", PerplexityParser.parse),
    ]

    for name, parser in parsers:
        try:
            result = parser(file_path)
            if result:
                print(f"Detected {name} format: {len(result)} conversations")
                return result
        except Exception as e:
            continue

    print("Could not detect export format")
    return []
