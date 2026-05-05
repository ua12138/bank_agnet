-- postgres_schema.sql
-- Task / result / approval tables for production deployment.

CREATE TABLE IF NOT EXISTS diagnosis_task (
    id BIGSERIAL PRIMARY KEY,
    incident_id VARCHAR(64) NOT NULL,
    system_name VARCHAR(64) NOT NULL,
    service_name VARCHAR(64),
    priority VARCHAR(16) NOT NULL DEFAULT 'P2',
    status VARCHAR(16) NOT NULL,
    payload_json JSONB NOT NULL,
    retry_count INT NOT NULL DEFAULT 0,
    max_retry INT NOT NULL DEFAULT 3,
    worker_id VARCHAR(64),
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    error_message TEXT,
    need_notify BOOLEAN NOT NULL DEFAULT TRUE,
    notify_status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_diagnosis_task_status_priority_created
ON diagnosis_task(status, priority, created_at);

CREATE TABLE IF NOT EXISTS diagnosis_result (
    id BIGSERIAL PRIMARY KEY,
    incident_id VARCHAR(64) NOT NULL,
    root_cause_top1 TEXT,
    root_cause_candidates JSONB,
    evidence_json JSONB,
    suggestions_json JSONB,
    confidence NUMERIC(5,4),
    llm_model VARCHAR(64),
    tool_trace_json JSONB,
    result_json JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_diagnosis_result_incident_id
ON diagnosis_result(incident_id);

CREATE TABLE IF NOT EXISTS approval_record (
    incident_id VARCHAR(64) PRIMARY KEY,
    status VARCHAR(32) NOT NULL,
    approver VARCHAR(128) NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

