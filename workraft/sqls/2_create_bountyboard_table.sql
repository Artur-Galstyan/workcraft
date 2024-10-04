CREATE TABLE IF NOT EXISTS bountyboard (
    id CHAR(36) PRIMARY KEY,
    status ENUM('PENDING', 'RUNNING', 'SUCCESS', 'FAILURE', 'INVALID') NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    worker_id VARCHAR(36),
    queue VARCHAR(255) DEFAULT 'DEFAULT',
    payload JSON,
    result JSON,
    retry_on_failure BOOLEAN DEFAULT FALSE,
    retry_count INT DEFAULT 0,
    retry_limit INT NOT NULL DEFAULT 0,
    CONSTRAINT chk_retry_limit CHECK (retry_limit >= 0),
    CONSTRAINT chk_retry_consistency CHECK (
        (retry_on_failure = false) OR (retry_on_failure = true AND retry_limit > 1)
    ),
    FOREIGN KEY (worker_id) REFERENCES peon(id)
);
