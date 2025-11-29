"""Database migrations for Supabase PostgreSQL with pgvector."""

import logging

from supabase import Client

logger = logging.getLogger(__name__)

MIGRATIONS = [
    # Migration 1: Enable pgvector extension
    {
        "name": "enable_pgvector",
        "sql": "CREATE EXTENSION IF NOT EXISTS vector;",
    },
    # Migration 2: Create articles table with vector column
    {
        "name": "create_articles_table",
        "sql": """
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            content TEXT NOT NULL DEFAULT '',
            summary TEXT,
            embedding VECTOR(1536),
            categories TEXT[] DEFAULT '{}',
            vulnerabilities TEXT[] DEFAULT '{}',
            threat_actors TEXT[] DEFAULT '{}',
            story_id TEXT,
            related_article_ids TEXT[] DEFAULT '{}',
            published_at TIMESTAMPTZ NOT NULL,
            scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
    },
    # Migration 3: Create indexes for articles
    {
        "name": "create_articles_indexes",
        "sql": """
        CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);
        """,
    },
    # Migration 4: Create predictions table
    {
        "name": "create_predictions_table",
        "sql": """
        CREATE TABLE IF NOT EXISTS predictions (
            prediction_id TEXT PRIMARY KEY,
            article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            prediction_type TEXT NOT NULL,
            description TEXT NOT NULL,
            confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
            timeframe_days INTEGER NOT NULL,
            reasoning TEXT,
            supporting_evidence TEXT[] DEFAULT '{}',
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
    },
    # Migration 5: Create predictions index
    {
        "name": "create_predictions_index",
        "sql": """
        CREATE INDEX IF NOT EXISTS idx_predictions_article_id ON predictions(article_id);
        """,
    },
    # Migration 6: Create graph_nodes table
    {
        "name": "create_graph_nodes_table",
        "sql": """
        CREATE TABLE IF NOT EXISTS graph_nodes (
            id TEXT PRIMARY KEY,
            node_type TEXT NOT NULL,
            label TEXT NOT NULL,
            properties JSONB DEFAULT '{}',
            size FLOAT DEFAULT 1.0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
    },
    # Migration 7: Create graph_edges table
    {
        "name": "create_graph_edges_table",
        "sql": """
        CREATE TABLE IF NOT EXISTS graph_edges (
            id SERIAL PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relationship TEXT NOT NULL,
            weight FLOAT DEFAULT 1.0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(source_id, target_id, relationship)
        );
        """,
    },
    # Migration 8: Create graph indexes
    {
        "name": "create_graph_indexes",
        "sql": """
        CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes(node_type);
        CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges(source_id);
        CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges(target_id);
        """,
    },
    # Migration 9: Create vector similarity search function
    {
        "name": "create_match_articles_function",
        "sql": """
        CREATE OR REPLACE FUNCTION match_articles(
            query_embedding VECTOR(1536),
            match_threshold FLOAT DEFAULT 0.75,
            match_count INT DEFAULT 5
        )
        RETURNS TABLE (
            id TEXT,
            title TEXT,
            url TEXT,
            summary TEXT,
            categories TEXT[],
            published_at TIMESTAMPTZ,
            similarity FLOAT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            SELECT
                a.id,
                a.title,
                a.url,
                a.summary,
                a.categories,
                a.published_at,
                1 - (a.embedding <=> query_embedding) AS similarity
            FROM articles a
            WHERE a.embedding IS NOT NULL
                AND 1 - (a.embedding <=> query_embedding) > match_threshold
            ORDER BY a.embedding <=> query_embedding
            LIMIT match_count;
        END;
        $$;
        """,
    },
    # Migration 10: Add scraper fields to articles table
    {
        "name": "add_scraper_fields",
        "sql": """
        ALTER TABLE articles
        ADD COLUMN IF NOT EXISTS author TEXT DEFAULT 'Unknown',
        ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
        ADD COLUMN IF NOT EXISTS thumbnail_url TEXT DEFAULT '',
        ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'rss';
        """,
    },
    # Migration 11: Create index on source column for filtering
    {
        "name": "create_source_index",
        "sql": """
        CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
        """,
    },
    # Migration 12: Create user_profiles table for notification preferences
    {
        "name": "create_user_profiles_table",
        "sql": """
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
        """,
    },
    # Migration 13: Create notification_interests table with embeddings
    {
        "name": "create_notification_interests_table",
        "sql": """
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
        """,
    },
    # Migration 14: Create telegram_links table for account linking
    {
        "name": "create_telegram_links_table",
        "sql": """
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
        """,
    },
    # Migration 15: Create notification_queue table
    {
        "name": "create_notification_queue_table",
        "sql": """
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
        """,
    },
    # Migration 16: Create notification_history table
    {
        "name": "create_notification_history_table",
        "sql": """
        CREATE TABLE IF NOT EXISTS notification_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
            channel TEXT NOT NULL,
            article_count INTEGER NOT NULL,
            digest_type TEXT,
            sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_notification_history_user ON notification_history(user_id, sent_at DESC);
        """,
    },
    # Migration 17: Create match_article_to_interests function
    {
        "name": "create_match_article_to_interests_function",
        "sql": """
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
        """,
    },
    # Migration 18: Create vector index for notification_interests
    {
        "name": "create_notification_interests_vector_index",
        "sql": """
        CREATE INDEX IF NOT EXISTS idx_notification_interests_embedding
        ON notification_interests USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """,
    },
]


async def run_migrations(client: Client) -> None:
    """Run all database migrations."""
    logger.info("Running database migrations...")

    for migration in MIGRATIONS:
        try:
            logger.info("Running migration: %s", migration["name"])
            result = client.rpc("exec_sql", {"sql": migration["sql"]}).execute()
            logger.info("Migration %s completed", migration["name"])
        except Exception as e:
            # Try direct execution via postgrest if rpc fails
            try:
                # For DDL statements, we need to use the SQL endpoint
                # The supabase-py client doesn't directly support raw SQL execution
                # So we'll log and continue - migrations should be run via Supabase dashboard
                logger.warning("Migration %s requires manual execution: %s", migration["name"], str(e))
            except Exception as inner_e:
                logger.error("Migration %s failed: %s", migration["name"], str(inner_e))

    logger.info("Database migrations completed")


def get_migration_sql() -> str:
    """Get all migration SQL as a single string for manual execution."""
    sql_parts = []
    for migration in MIGRATIONS:
        sql_parts.append(f"-- Migration: {migration['name']}")
        sql_parts.append(migration["sql"].strip())
        sql_parts.append("")

    return "\n".join(sql_parts)
