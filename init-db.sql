-- EJE Database Initialization Script
-- Creates necessary tables and indexes for PostgreSQL

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Audit Log Table
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    request_id UUID NOT NULL UNIQUE,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    input_case JSONB NOT NULL,
    critic_outputs JSONB NOT NULL,
    final_decision JSONB NOT NULL,
    precedent_refs JSONB,
    from_cache BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_request_id ON audit_log(request_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_verdict ON audit_log((final_decision->>'overall_verdict'));

-- Signed Audit Log Table (with cryptographic signatures for tamper detection)
CREATE TABLE IF NOT EXISTS signed_audit_log (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decision_data TEXT NOT NULL,
    signature VARCHAR(64) NOT NULL,
    key_version VARCHAR(16) NOT NULL DEFAULT 'v1',
    version VARCHAR(16) NOT NULL DEFAULT '1.0'
);

CREATE INDEX IF NOT EXISTS idx_signed_audit_log_request_id ON signed_audit_log(request_id);
CREATE INDEX IF NOT EXISTS idx_signed_audit_log_timestamp ON signed_audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signed_audit_log_key_version ON signed_audit_log(key_version);

-- Precedent Table
CREATE TABLE IF NOT EXISTS precedents (
    id SERIAL PRIMARY KEY,
    precedent_id UUID NOT NULL UNIQUE DEFAULT uuid_generate_v4(),
    case_hash VARCHAR(64) NOT NULL,
    input_case JSONB NOT NULL,
    decision JSONB NOT NULL,
    embedding VECTOR(768),  -- For semantic search (requires pgvector extension)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for precedent lookup
CREATE INDEX IF NOT EXISTS idx_precedents_case_hash ON precedents(case_hash);
CREATE INDEX IF NOT EXISTS idx_precedents_created_at ON precedents(created_at DESC);

-- Feedback Table (for human corrections and improvements)
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    request_id UUID NOT NULL REFERENCES audit_log(request_id),
    feedback_type VARCHAR(50) NOT NULL,  -- 'correction', 'approval', 'concern'
    original_verdict VARCHAR(50),
    corrected_verdict VARCHAR(50),
    feedback_text TEXT,
    submitted_by VARCHAR(255),
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_request_id ON feedback(request_id);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type);

-- Critic Performance Table (for monitoring)
CREATE TABLE IF NOT EXISTS critic_performance (
    id SERIAL PRIMARY KEY,
    critic_name VARCHAR(100) NOT NULL,
    total_calls INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0,
    total_timeouts INTEGER DEFAULT 0,
    avg_response_time_ms FLOAT,
    last_error TEXT,
    last_error_at TIMESTAMP,
    last_success_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(critic_name)
);

CREATE INDEX IF NOT EXISTS idx_critic_performance_name ON critic_performance(critic_name);

-- View for decision statistics
CREATE OR REPLACE VIEW decision_stats AS
SELECT 
    DATE(timestamp) as date,
    final_decision->>'overall_verdict' as verdict,
    COUNT(*) as count,
    AVG((final_decision->>'avg_confidence')::float) as avg_confidence,
    COUNT(*) FILTER (WHERE from_cache = true) as cached_count
FROM audit_log
GROUP BY DATE(timestamp), final_decision->>'overall_verdict'
ORDER BY date DESC, verdict;

-- View for critic agreement analysis
CREATE OR REPLACE VIEW critic_agreement AS
SELECT 
    request_id,
    timestamp,
    jsonb_array_length(critic_outputs) as num_critics,
    (
        SELECT COUNT(DISTINCT (output->>'verdict'))
        FROM jsonb_array_elements(critic_outputs) as output
    ) as unique_verdicts
FROM audit_log
ORDER BY timestamp DESC;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO eje_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO eje_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO eje_user;

-- Insert initial test data (optional - comment out for production)
-- INSERT INTO audit_log (request_id, input_case, critic_outputs, final_decision)
-- VALUES (
--     uuid_generate_v4(),
--     '{"text": "Test case for system initialization"}'::jsonb,
--     '[]'::jsonb,
--     '{"overall_verdict": "ALLOW", "reason": "System test"}'::jsonb
-- );

COMMIT;
