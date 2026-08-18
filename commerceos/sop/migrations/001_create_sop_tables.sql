CREATE TABLE IF NOT EXISTS sop_definitions (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    trigger VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    enabled BOOLEAN NOT NULL DEFAULT 1,
    severity VARCHAR(20) NOT NULL DEFAULT 'warning',
    steps JSON NOT NULL DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_sop_definitions_code ON sop_definitions(code);
CREATE INDEX IF NOT EXISTS ix_sop_definitions_enabled ON sop_definitions(enabled, category);

CREATE TABLE IF NOT EXISTS sop_executions (
    id VARCHAR(36) PRIMARY KEY,
    sop_code VARCHAR(50) NOT NULL,
    store_id VARCHAR(50) NOT NULL,
    execution_id VARCHAR(100) NOT NULL UNIQUE,
    applies BOOLEAN NOT NULL DEFAULT 0,
    branches JSON NOT NULL DEFAULT '[]',
    outputs JSON NOT NULL DEFAULT '{}',
    errors JSON NOT NULL DEFAULT '[]',
    executed_at TIMESTAMP NOT NULL,
    source_run_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_sop_executions_sop_code ON sop_executions(sop_code);
CREATE INDEX IF NOT EXISTS ix_sop_executions_store_id ON sop_executions(store_id);
CREATE INDEX IF NOT EXISTS ix_sop_executions_execution_id ON sop_executions(execution_id);
CREATE INDEX IF NOT EXISTS ix_sop_executions_store_executed ON sop_executions(store_id, executed_at);
