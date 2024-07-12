CREATE OR REPLACE FUNCTION self_correct_tasks() RETURNS void AS $$
DECLARE
    task_record RECORD;
    affected_count INT := 0;
BEGIN
    -- Look for tasks that are RUNNING but the assigned worker is:
    -- 1. not in the peon table (worker doesn't exist)
    -- 2. in the IDLE or OFFLINE state
    -- 3. working on a different task
    FOR task_record IN
        SELECT b.id, b.queue
        FROM bountyboard b
        LEFT JOIN peon p ON b.worker_id = p.id
        WHERE b.status = 'RUNNING'
        AND (p.id IS NULL OR p.status IN ('IDLE', 'OFFLINE') OR p.current_task != b.id)
    LOOP
        affected_count := affected_count + 1;
        UPDATE bountyboard
        SET status = 'PENDING'::task_status, worker_id = NULL
        WHERE id = task_record.id;
        PERFORM pg_notify('new_task', task_record.id::text || '§' || task_record.queue);
        RAISE NOTICE 'Task % in queue % reset to PENDING.', task_record.id, task_record.queue;
    END LOOP;

    IF affected_count > 0 THEN
        RAISE NOTICE '% task(s) reset to PENDING.', affected_count;
    ELSE
        RAISE NOTICE 'No tasks needed resetting.';
    END IF;
END;
$$ LANGUAGE plpgsql;
