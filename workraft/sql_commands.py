SETUP = """
CREATE TABLE IF NOT EXISTS peon (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL,
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    current_task UUID
);

CREATE TABLE IF NOT EXISTS bountyboard (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    worker_id UUID REFERENCES peon(id),
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


CREATE OR REPLACE FUNCTION refire_pending_tasks() RETURNS void AS $$
DECLARE
    task_id UUID;
BEGIN
    FOR task_id IN SELECT id FROM bountyboard WHERE status = 'PENDING' LOOP
        PERFORM pg_notify('new_task', task_id::text);
        RAISE NOTICE 'Notified task: %', task_id;
    END LOOP;

    IF NOT FOUND THEN
        RAISE NOTICE 'No pending tasks found';
    END IF;
END;
$$ LANGUAGE plpgsql;


-- First, enable pg_cron extension if not already enabled
CREATE EXTENSION IF NOT EXISTS pg_cron;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM cron.job WHERE command = 'SELECT refire_pending_tasks()') THEN
    PERFORM cron.schedule('* * * * *', 'SELECT refire_pending_tasks()');
  END IF;
END $$;
"""
