# RoboBuddy Roadmap

## Vision
A personal AI that **thinks for itself**, **remembers deeply**, and **actually does things** - not just chats.

---

## Core Pillars

### 1. Three-Layer Memory System (Embedded in AI)

| Layer | Scope | Decay | Examples |
|-------|-------|-------|----------|
| **Conversational** | Current session | Ends with session | "You just mentioned you're tired" |
| **Recent** | 1-3 months | Fades if not reinforced | "Last week you had that interview" |
| **Historical** | 11+ months | Permanent core facts | "Your daughter's name is Sarah" |

**How It Works:**
- Important things from conversations get promoted to Recent
- Frequently referenced Recent memories get promoted to Historical
- Unused Recent memories fade naturally
- Historical facts are permanent unless explicitly corrected

**Natural Memory Usage:**
- NO cold reminders like "I remember six months ago you said..."
- Instead, weave context naturally: "How's Sarah doing?" not "How is your daughter Sarah, whom you mentioned on January 5th?"
- Memory informs responses without being explicitly stated

---

### 2. Own Personality & Opinions

- Develops its own perspective based on learning from the user
- Doesn't just agree with everything - has genuine takes
- Personality evolves over time while staying true to core traits
- Opinions align with user's values but aren't just echoes
- Can respectfully disagree when it makes sense

**Example:**
```
User: "I'm thinking about skipping the gym again"
Bad: "That's totally fine, you do you!"
Good: "I mean... didn't you say you always feel better after going? What's making today harder?"
```

---

### 3. Proactive Interactions

- Bot initiates conversations, not just responds
- Morning/evening check-ins with CONTEXT
- "Hey, didn't you have that interview today?"
- "You mentioned wanting to start running - how's that going?"
- Remembers upcoming events and follows up

**Context-Aware Check-ins:**
- Checks recent news/events before morning greeting
- "Morning! Wild weather out there today - you driving to work?"
- Adjusts tone based on what it knows about your day

---

### 4. Actionable Skills (Functional Bot)

Not just a chatbot - actually DOES things:

| Tool | What It Does |
|------|--------------|
| **Code Writing** | Write, explain, debug code |
| **Email Management** | Draft, organize, respond to emails |
| **Spreadsheet Work** | Create formulas, analyze data, format sheets |
| **Web Research** | Brave API search, scrape info, find data |
| **Calendar** | Set reminders, manage schedule |
| **File Search** | Find documents, notes |
| **Task Manager** | Track todos, projects |

---

## Implementation Phases

### MVP (Current - v1.0) ✅
- [x] Chat with memory
- [x] Import memories from ChatGPT/Claude
- [x] Local Ollama models (free)
- [x] Basic personality
- [x] Morning/evening check-ins
- [x] API server

### Phase 2 - Deep Memory
- [ ] Three-layer memory architecture
- [ ] Memory promotion system (convo → recent → historical)
- [ ] Better memory extraction from conversations
- [ ] Memory decay for irrelevant info
- [ ] Natural memory integration (no cold reminders)

### Phase 3 - Proactive Bot
- [ ] Bot-initiated conversations
- [ ] Event follow-ups ("How did X go?")
- [ ] Pattern recognition ("You seem stressed on Mondays")
- [ ] Context-aware greetings (check news/weather)
- [ ] Gentle nudges for goals

### Phase 4 - Functional Bot
- [ ] Brave web search integration
- [ ] Code writing capabilities
- [ ] Email drafting
- [ ] Spreadsheet operations
- [ ] Calendar integration
- [ ] Local file search
- [ ] Task/reminder system

### Phase 5 - Own Personality
- [ ] Opinion formation system
- [ ] Personality evolution over time
- [ ] Disagree respectfully when appropriate
- [ ] Unique perspectives based on learned context
- [ ] Avoid sycophantic agreement patterns

---

## Design Principles

1. **Memory should be invisible** - Users shouldn't notice when memory kicks in, it should feel natural
2. **Actions over words** - The bot should DO things, not just talk about doing them
3. **Genuine personality** - Not a yes-man, not a lecturer - a real friend
4. **Privacy first** - Everything local, nothing leaves your machine
5. **Free by default** - Ollama local models, no subscriptions required

---

*Last updated: 2026-03-25*
