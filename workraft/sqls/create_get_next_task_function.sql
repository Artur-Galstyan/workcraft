CREATE OR REPLACE FUNCTION get_next_task(in_worker_id UUID) RETURNS UUID AS $$
DECLARE
    next_task_id UUID;
    worker_queues TEXT[];
BEGIN
    -- Get the worker's queues
    SELECT queues INTO worker_queues
    FROM peon
    WHERE id = in_worker_id;

    -- Attempt to get and claim the next task in one step
    WITH next_task AS (
        DELETE FROM task_queue
        WHERE task_id IN (
            SELECT b.id
            FROM bountyboard b
            WHERE b.status = 'PENDING' AND b.queue = ANY(worker_queues)
            ORDER BY b.created_at
            LIMIT 1
        )
        RETURNING task_id
    )
    UPDATE bountyboard b
    SET status = 'RUNNING', worker_id = in_worker_id
    FROM next_task
    WHERE b.id = next_task.task_id
    RETURNING b.id INTO next_task_id;

    IF next_task_id IS NOT NULL THEN
        RAISE NOTICE 'Worker % successfully claimed task %', in_worker_id, next_task_id;
    END IF;

    RETURN next_task_id;
END;
$$ LANGUAGE plpgsql;
