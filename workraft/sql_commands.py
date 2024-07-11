SETUP = """
-- Create ENUM types
CREATE TYPE worker_status AS ENUM ('IDLE', 'PREPARING', 'WORKING', 'OFFLINE');
CREATE TYPE task_status AS ENUM ('PENDING', 'RUNNING', 'SUCCESS', 'FAILURE');

-- Create tables
CREATE TABLE IF NOT EXISTS peon (
    id UUID PRIMARY KEY,
    status worker_status NOT NULL DEFAULT 'IDLE',
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    current_task UUID
);

CREATE TABLE IF NOT EXISTS bountyboard (
    id UUID PRIMARY KEY,
    status task_status NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    worker_id UUID REFERENCES peon(id),
    payload JSONB,
    result JSONB
);

CREATE TABLE IF NOT EXISTS task_queue (
    id SERIAL PRIMARY KEY,
    task_id UUID REFERENCES bountyboard(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_peon_status_heartbeat ON peon(status, last_heartbeat);
CREATE INDEX idx_bountyboard_status ON bountyboard(status);

-- Notification function
CREATE OR REPLACE FUNCTION notify_new_task() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO task_queue (task_id) VALUES (NEW.id);
    PERFORM pg_notify('new_task', NEW.id::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS task_inserted_trigger ON bountyboard;
CREATE TRIGGER task_inserted_trigger
AFTER INSERT ON bountyboard
FOR EACH ROW
WHEN (NEW.status = 'PENDING')
EXECUTE FUNCTION notify_new_task();

CREATE TRIGGER task_updated_to_pending_trigger
AFTER UPDATE ON bountyboard
FOR EACH ROW
WHEN (OLD.status != 'PENDING' AND NEW.status = 'PENDING')
EXECUTE FUNCTION notify_new_task();

-- Get next task function
CREATE OR REPLACE FUNCTION get_next_task(in_worker_id UUID) RETURNS UUID AS $$
DECLARE
    next_task_id UUID;
    rows_affected INT;
BEGIN
    LOOP
        -- Attempt to get the next task
        SELECT task_id INTO next_task_id
        FROM task_queue
        ORDER BY created_at
        LIMIT 1;

        -- If no task is available, return NULL
        IF next_task_id IS NULL THEN
            RETURN NULL;
        END IF;

        -- Attempt to delete the task from the queue
        DELETE FROM task_queue
        WHERE task_id = next_task_id
        AND id = (SELECT id FROM task_queue WHERE task_id = next_task_id);

        GET DIAGNOSTICS rows_affected = ROW_COUNT;

        IF rows_affected > 0 THEN
            -- Task successfully claimed, update related tables
            UPDATE bountyboard
            SET status = 'RUNNING', worker_id = in_worker_id
            WHERE id = next_task_id;

            -- Log the successful claim
            RAISE NOTICE 'Worker % successfully claimed task %', in_worker_id, next_task_id;

            RETURN next_task_id;
        END IF;

        -- If we reach here, another worker claimed the task first
        RAISE NOTICE 'Task % was claimed by another worker, trying again', next_task_id;
        -- The loop will continue and try to get the next task
    END LOOP;
END;
$$ LANGUAGE plpgsql;


-- Heartbeat function
CREATE OR REPLACE FUNCTION heartbeat(in_worker_id UUID) RETURNS void AS $$
BEGIN
    UPDATE peon
    SET last_heartbeat = NOW()
    WHERE id = in_worker_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION send_refire_signal(in_worker_id UUID) RETURNS INTEGER AS $$
DECLARE
    task_id UUID;
    tasks_sent INTEGER := 0;
BEGIN
    FOR task_id IN SELECT id FROM bountyboard WHERE status = 'PENDING' LOOP
        PERFORM pg_notify(in_worker_id::text, task_id::text);

        tasks_sent := tasks_sent + 1;
        RAISE NOTICE 'Notified task: %', task_id;
    END LOOP;

    IF tasks_sent = 0 THEN
        RAISE NOTICE 'No pending tasks found';
    ELSE
        RAISE NOTICE 'Notified % pending task(s)', tasks_sent;
    END IF;

    RETURN tasks_sent;
END;
$$ LANGUAGE plpgsql;


-- Refire pending tasks function
CREATE OR REPLACE FUNCTION refire_pending_tasks_for_all() RETURNS INTEGER AS $$
DECLARE
    task_id UUID;
    tasks_sent INTEGER := 0;
BEGIN
    FOR task_id IN SELECT id FROM bountyboard WHERE status = 'PENDING' LOOP
        PERFORM pg_notify('new_task', task_id::text);
        RAISE NOTICE 'Notified task: %', task_id;
        tasks_sent := tasks_sent + 1;
    END LOOP;

    IF tasks_sent = 0 THEN
        RAISE NOTICE 'No pending tasks found';
    ELSE
        RAISE NOTICE 'Notified % pending task(s)', tasks_sent;
    END IF;

    RETURN tasks_sent;
END;
$$ LANGUAGE plpgsql;

-- Check dead workers function
CREATE OR REPLACE FUNCTION check_dead_workers() RETURNS void AS $$
DECLARE
    dead_worker RECORD;
    affected_count INT := 0;
BEGIN
    FOR dead_worker IN
        SELECT id, current_task
        FROM peon
        WHERE status = 'IDLE'
          AND last_heartbeat < NOW() - INTERVAL '5 minutes'
        FOR UPDATE
    LOOP
        affected_count := affected_count + 1;

        IF dead_worker.current_task IS NOT NULL THEN
            UPDATE bountyboard
            SET status = 'PENDING'::task_status, worker_id = NULL
            WHERE id = dead_worker.current_task AND status = 'RUNNING';

            PERFORM pg_notify('new_task', dead_worker.current_task::text);
            RAISE NOTICE 'Worker % marked as offline. Task % reset.', dead_worker.id, dead_worker.current_task;
        ELSE
            RAISE NOTICE 'Worker % marked as offline. No task was assigned.', dead_worker.id;
        END IF;

        UPDATE peon
        SET status = 'OFFLINE'::worker_status, current_task = NULL
        WHERE id = dead_worker.id;
    END LOOP;

    IF affected_count > 0 THEN
        RAISE NOTICE '% dead worker(s) processed.', affected_count;
    ELSE
        RAISE NOTICE 'No dead workers found.';
    END IF;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION self_correct_tasks() RETURNS void AS $$
DECLARE
    task_id UUID;
    affected_count INT := 0;
BEGIN
    -- Look for tasks that are RUNNING but the assigned worker is:
    -- 1. not in the peon table (worker doesn't exist)
    -- 2. in the IDLE or OFFLINE state
    -- 3. working on a different task
    FOR task_id IN
        SELECT b.id
        FROM bountyboard b
        LEFT JOIN peon p ON b.worker_id = p.id
        WHERE b.status = 'RUNNING'
        AND (p.id IS NULL OR p.status IN ('IDLE', 'OFFLINE') OR p.current_task != b.id)
    LOOP
        affected_count := affected_count + 1;
        UPDATE bountyboard
        SET status = 'PENDING'::task_status, worker_id = NULL
        WHERE id = task_id;
        PERFORM pg_notify('new_task', task_id::text);
        RAISE NOTICE 'Task % reset to PENDING.', task_id;
    END LOOP;

    IF affected_count > 0 THEN
        RAISE NOTICE '% task(s) reset to PENDING.', affected_count;
    ELSE
        RAISE NOTICE 'No tasks needed resetting.';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Schedule cron jobs
CREATE EXTENSION IF NOT EXISTS pg_cron;

DO $$
    BEGIN
    IF NOT EXISTS (SELECT 1 FROM cron.job WHERE command = 'SELECT refire_pending_tasks_for_all()') THEN
        PERFORM cron.schedule('* * * * *', 'SELECT refire_pending_tasks_for_all()');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM cron.job WHERE command = 'SELECT check_dead_workers()') THEN
        PERFORM cron.schedule('* * * * *', 'SELECT check_dead_workers()');
    END IF;
        IF NOT EXISTS (SELECT 1 FROM cron.job WHERE command = 'SELECT self_correct_tasks()') THEN
        PERFORM cron.schedule('* * * * *', 'SELECT self_correct_tasks()');
    END IF;
END $$;

"""
