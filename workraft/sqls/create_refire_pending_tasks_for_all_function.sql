CREATE OR REPLACE FUNCTION refire_pending_tasks_for_all() RETURNS INTEGER AS $$
DECLARE
    task_record RECORD;
    tasks_sent INTEGER := 0;
BEGIN
    FOR task_record IN SELECT id, queue FROM bountyboard WHERE status = 'PENDING'
    LOOP
        PERFORM pg_notify('new_task', task_record.id::text || '§' || task_record.queue);
        RAISE NOTICE 'Notified task: % in queue %', task_record.id, task_record.queue;
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
