-- ============================================================================
-- KB Architecture Tables - Event-Sourced Versioned Knowledge Base
-- Run against Cloud SQL PostgreSQL to initialize the schema.
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. kb_versions: Immutable version records
CREATE TABLE IF NOT EXISTS kb_versions (
    version_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_number INTEGER NOT NULL,
    version_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    author VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    checksum VARCHAR(64) NOT NULL,
    parent_version_id UUID REFERENCES kb_versions(version_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_kb_versions_is_active ON kb_versions (is_active);
CREATE INDEX IF NOT EXISTS ix_kb_versions_created_at ON kb_versions (created_at);

-- 2. kb_modules: JSONB snapshots per module per version
CREATE TABLE IF NOT EXISTS kb_modules (
    module_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES kb_versions(version_id),
    module_name VARCHAR(100) NOT NULL,
    module_data JSONB NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_version_module UNIQUE (version_id, module_name)
);

CREATE INDEX IF NOT EXISTS ix_kb_modules_version_id ON kb_modules (version_id);
CREATE INDEX IF NOT EXISTS ix_kb_modules_module_name ON kb_modules (module_name);

-- 3. kb_audit_log: Append-only audit trail
CREATE TABLE IF NOT EXISTS kb_audit_log (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action VARCHAR(50) NOT NULL,
    actor VARCHAR(255) NOT NULL,
    target_version_id UUID,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_kb_audit_log_timestamp ON kb_audit_log (timestamp);
CREATE INDEX IF NOT EXISTS ix_kb_audit_log_action ON kb_audit_log (action);
CREATE INDEX IF NOT EXISTS ix_kb_audit_log_actor ON kb_audit_log (actor);
