SETUP = """
CREATE TABLE IF NOT EXISTS warband (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL,
    last_heartbeat TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS bountyboard (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    worker_id UUID REFERENCES warband(id),
    payload JSONB,
    result JSONB
);

CREATE OR REPLACE FUNCTION notify_new_task() RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('new_task', NEW.id::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS task_inserted_trigger ON bountyboard;
CREATE TRIGGER task_inserted_trigger
AFTER INSERT ON bountyboard
FOR EACH ROW
EXECUTE FUNCTION notify_new_task();
"""
