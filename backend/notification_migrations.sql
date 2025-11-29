-- Notification System Migrations
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/YOUR_PROJECT/sql

-- Migration 12: Create user_profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY,
    email TEXT,
    display_name TEXT,
    digest_frequency TEXT DEFAULT 'daily' CHECK (digest_frequency IN ('hourly', 'daily', 'weekly')),
    email_enabled BOOLEAN DEFAULT true,
    telegram_enabled BOOLEAN DEFAULT false,
    last_digest_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_profiles_digest ON user_profiles(digest_frequency, last_digest_sent_at);

-- Migration 13: Create notification_interests table
CREATE TABLE IF NOT EXISTS notification_interests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    interest_text TEXT NOT NULL,
    embedding VECTOR(1536),
    similarity_threshold FLOAT DEFAULT 0.8,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_notification_interests_user ON notification_interests(user_id, is_active);

-- Migration 14: Create telegram_links table
CREATE TABLE IF NOT EXISTS telegram_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    telegram_chat_id BIGINT UNIQUE,
    telegram_username TEXT,
    link_token TEXT UNIQUE,
    token_expires_at TIMESTAMPTZ,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_telegram_links_token ON telegram_links(link_token);

-- Migration 15: Create notification_queue table
CREATE TABLE IF NOT EXISTS notification_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    interest_id UUID REFERENCES notification_interests(id) ON DELETE SET NULL,
    similarity_score FLOAT NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('email', 'telegram')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    UNIQUE(user_id, article_id, channel)
);
CREATE INDEX IF NOT EXISTS idx_notification_queue_pending ON notification_queue(status, user_id);

-- Migration 16: Create notification_history table
CREATE TABLE IF NOT EXISTS notification_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    article_count INTEGER NOT NULL,
    digest_type TEXT,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_notification_history_user ON notification_history(user_id, sent_at DESC);

-- Migration 17: Create match_article_to_interests function
CREATE OR REPLACE FUNCTION match_article_to_interests(
    article_embedding VECTOR(1536),
    min_threshold FLOAT DEFAULT 0.8
)
RETURNS TABLE (
    interest_id UUID,
    user_id UUID,
    interest_text TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ni.id AS interest_id,
        ni.user_id,
        ni.interest_text,
        1 - (ni.embedding <=> article_embedding) AS similarity
    FROM notification_interests ni
    JOIN user_profiles up ON ni.user_id = up.id
    WHERE ni.is_active = true
      AND ni.embedding IS NOT NULL
      AND 1 - (ni.embedding <=> article_embedding) >= GREATEST(min_threshold, ni.similarity_threshold)
    ORDER BY similarity DESC;
END;
$$;

-- Migration 18: Create vector index for notification_interests
CREATE INDEX IF NOT EXISTS idx_notification_interests_embedding
ON notification_interests USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
