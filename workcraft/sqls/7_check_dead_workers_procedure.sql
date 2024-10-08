CREATE PROCEDURE check_dead_workers()
BEGIN
    DECLARE dead_worker_id VARCHAR(36);
    DECLARE dead_worker_task CHAR(36);
    DECLARE affected_count INT DEFAULT 0;
    DECLARE task_queue VARCHAR(255);
    DECLARE done INT DEFAULT FALSE;
    DECLARE cur CURSOR FOR
        SELECT id, current_task
        FROM peon
        WHERE status = 'IDLE'
          AND last_heartbeat < NOW() - INTERVAL {DB_SETUP_WAIT_TIME_BEFORE_WORKER_DECLARED_DEAD} SECOND
        FOR UPDATE;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    START TRANSACTION;

    OPEN cur;

    read_loop: LOOP
        FETCH cur INTO dead_worker_id, dead_worker_task;
        IF done THEN
            LEAVE read_loop;
        END IF;

        SET affected_count = affected_count + 1;

        IF dead_worker_task IS NOT NULL THEN
            -- Get the queue of the task
            SELECT queue INTO task_queue
            FROM bountyboard
            WHERE id = dead_worker_task;

            UPDATE bountyboard
            SET status = 'PENDING', worker_id = NULL
            WHERE id = dead_worker_task AND status = 'RUNNING';

            -- Log the action
            INSERT INTO logs (message)
            VALUES (CONCAT('Worker ', dead_worker_id, ' marked as offline. Task ', dead_worker_task, ' in queue ', task_queue, ' reset.'));
        ELSE
            -- Log the action
            INSERT INTO logs (message)
            VALUES (CONCAT('Worker ', dead_worker_id, ' marked as offline. No task was assigned.'));
        END IF;

        UPDATE peon
        SET status = 'OFFLINE', current_task = NULL
        WHERE id = dead_worker_id;
    END LOOP;

    CLOSE cur;

    COMMIT;
END
