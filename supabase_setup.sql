-- BotBuddy Supabase Tables
-- Run this in your Supabase SQL Editor

-- Users table
CREATE TABLE IF NOT EXISTS botbuddy_users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,
    username TEXT,
    email TEXT UNIQUE,
    password_hash TEXT,
    buddy_name TEXT DEFAULT 'Buddy',
    personality TEXT DEFAULT 'friendly',
    voice TEXT DEFAULT 'samantha',
    timezone TEXT DEFAULT 'America/Chicago',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_interaction TIMESTAMPTZ DEFAULT NOW()
);

-- Memories table
CREATE TABLE IF NOT EXISTS botbuddy_memories (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES botbuddy_users(user_id) ON DELETE CASCADE,
    memory_type TEXT DEFAULT 'fact',
    content TEXT NOT NULL,
    importance TEXT DEFAULT 'medium',
    keywords TEXT[] DEFAULT '{}',
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations table
CREATE TABLE IF NOT EXISTS botbuddy_conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES botbuddy_users(user_id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    message_count INT DEFAULT 0
);

-- Messages table
CREATE TABLE IF NOT EXISTS botbuddy_messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID REFERENCES botbuddy_conversations(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    detected_mood TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analytics table (anonymous, aggregated)
CREATE TABLE IF NOT EXISTS botbuddy_analytics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    event_type TEXT NOT NULL,
    event_count INT DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily stats for dashboard
CREATE TABLE IF NOT EXISTS botbuddy_daily_stats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE UNIQUE NOT NULL DEFAULT CURRENT_DATE,
    total_users INT DEFAULT 0,
    new_users INT DEFAULT 0,
    total_messages INT DEFAULT 0,
    total_memories INT DEFAULT 0,
    active_users INT DEFAULT 0
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_memories_user ON botbuddy_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON botbuddy_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON botbuddy_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_date ON botbuddy_analytics(created_at);

-- Enable Row Level Security (optional, for extra security)
ALTER TABLE botbuddy_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE botbuddy_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE botbuddy_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE botbuddy_messages ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can do everything
CREATE POLICY "Service role full access" ON botbuddy_users FOR ALL USING (true);
CREATE POLICY "Service role full access" ON botbuddy_memories FOR ALL USING (true);
CREATE POLICY "Service role full access" ON botbuddy_conversations FOR ALL USING (true);
CREATE POLICY "Service role full access" ON botbuddy_messages FOR ALL USING (true);
