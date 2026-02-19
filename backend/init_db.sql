-- Database initialization script for Panelin Chat
-- Run this script once before deploying the application
-- For Cloud SQL: gcloud sql connect <instance-name> --user=postgres --database=app_database < init_db.sql

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries by user_id
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Create index for faster queries by created_at
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
