CREATE TABLE IF NOT EXISTS peon (
    id UUID PRIMARY KEY,
    status worker_status NOT NULL DEFAULT 'IDLE',
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    current_task UUID,
    queues TEXT[] DEFAULT ARRAY['DEFAULT']
);

CREATE TABLE IF NOT EXISTS bountyboard (
    id UUID PRIMARY KEY,
    status task_status NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    worker_id UUID REFERENCES peon(id),
    queue TEXT DEFAULT 'DEFAULT',
    payload JSONB,
    result JSONB
);

CREATE TABLE IF NOT EXISTS task_queue (
    id SERIAL PRIMARY KEY,
    task_id UUID REFERENCES bountyboard(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
