# BotBuddy

**Your AI Helper That Actually Remembers You**

A personal AI assistant that learns who you are, remembers your conversations, and proactively checks in. Unlike typical chatbots, BotBuddy actually knows you.

## Features

- **Import Memories** - Bring your history from ChatGPT, Claude, Gemini
- **Real Memory** - Remembers names, events, relationships, preferences
- **100% Free** - Uses local Ollama models, no API costs
- **100% Private** - All data stays on your computer
- **Proactive Check-ins** - Morning/evening greetings, event follow-ups
- **Mood Aware** - Detects how you're feeling and adjusts tone
- **Natural Personality** - Warm, curious, occasionally witty
- **Customizable** - Name your buddy whatever you want

## Quick Start

### 1. Install Ollama Models (one-time)

```bash
ollama pull gemma3:12b      # For conversation
ollama pull llama3.2        # For quick tasks
```

### 2. Configure & Run

```bash
cd ~/Projects/companion-app
cp .env.example .env
pip install -r requirements.txt
python chat.py
```

### 3. Import Your History (Optional)

Export your data from ChatGPT (Settings > Data Controls > Export), then:

```bash
python import_memories.py ~/Downloads/chatgpt_export.zip --preview  # See what will be imported
python import_memories.py ~/Downloads/chatgpt_export.zip            # Import it
```

## How Memory Import Works

1. **Export from ChatGPT/Claude/Gemini** - Use their built-in export feature
2. **Run the import script** - Parses your conversations
3. **AI extracts facts about you** - Names, preferences, relationships, events
4. **Stored in local database** - Your buddy now knows you

Example:
```
Before: "Hi! My name is..."
After:  "Hey Joe! How did that job interview go? And how's Sarah doing?"
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/chat` | POST | Send message, get response |
| `/api/v1/greeting/{user_id}` | GET | Get personalized greeting |
| `/api/v1/import/text` | POST | Import from pasted text |
| `/api/v1/memories/{user_id}` | GET | View stored memories |
| `/api/v1/settings` | GET/PUT | View/change buddy name |

## Memory Types

| Type | What It Stores | Example |
|------|----------------|---------|
| **fact** | Static info | "Name is Joe" |
| **episodic** | Events | "Doctor appointment Tuesday" |
| **emotional** | Mood patterns | "Anxious about work" |
| **preference** | Likes/dislikes | "Loves coffee" |
| **relationship** | People | "Daughter named Sarah" |

## Why BotBuddy?

| Feature | ChatGPT | Replika | **BotBuddy** |
|---------|---------|---------|--------------|
| Remembers everything | Forgets | Kinda | Forever |
| Runs locally/private | Cloud | Cloud | Local |
| Proactive check-ins | No | No | Yes |
| Import old AI memories | No | No | **Unique!** |
| Cost | $20/mo | $15/mo | **Free** |

## Data Storage

All data stored locally at `~/.botbuddy/botbuddy.db` (SQLite).

- No cloud
- No subscriptions
- No data leaves your computer

## Project Structure

```
botbuddy/
├── app/
│   ├── main.py              # FastAPI server
│   ├── config.py            # Settings
│   ├── api/routes.py        # API endpoints
│   ├── core/brain.py        # Multi-model router
│   ├── memory/              # SQLite storage
│   ├── personality/         # Buddy's soul
│   ├── importer/            # Memory import system
│   └── notifications/       # SMS (optional)
├── chat.py                  # Terminal chat
├── import_memories.py       # Memory import CLI
└── requirements.txt
```

## Commands

```bash
python chat.py                    # Chat in terminal
python import_memories.py FILE    # Import memories
./run.sh                          # Start API server
```

## License

MIT
