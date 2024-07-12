CREATE OR REPLACE FUNCTION check_dead_workers() RETURNS void AS $$
DECLARE
    dead_worker RECORD;
    affected_count INT := 0;
    task_queue TEXT;
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
            -- Get the queue of the task
            SELECT queue INTO task_queue
            FROM bountyboard
            WHERE id = dead_worker.current_task;

            UPDATE bountyboard
            SET status = 'PENDING'::task_status, worker_id = NULL
            WHERE id = dead_worker.current_task AND status = 'RUNNING';

            PERFORM pg_notify('new_task', dead_worker.current_task::text || '§' || task_queue);
            RAISE NOTICE 'Worker % marked as offline. Task % in queue % reset.', dead_worker.id, dead_worker.current_task, task_queue;
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
