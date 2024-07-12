CREATE OR REPLACE FUNCTION send_refire_signal(in_worker_id UUID) RETURNS INTEGER AS $$
DECLARE
    task_id UUID;
    tasks_sent INTEGER := 0;
    queue_name TEXT;
BEGIN
    FOR task_id, queue_name IN SELECT id, queue FROM bountyboard WHERE status = 'PENDING' LOOP
        PERFORM pg_notify(in_worker_id::text, task_id::text || '§' || queue_name::text);
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
