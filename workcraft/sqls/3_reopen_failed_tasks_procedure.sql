CREATE PROCEDURE reopen_failed_tasks()
BEGIN
    DECLARE task_id CHAR(36);
    DECLARE task_retry_count INT;
    DECLARE task_updated_at TIMESTAMP;
    DECLARE backoff_time INT;
    DECLARE done INT DEFAULT FALSE;
    DECLARE cur CURSOR FOR
        SELECT id, retry_count, updated_at
        FROM bountyboard
        WHERE status = 'FAILED'
          AND retry_on_failure = true
          AND retry_limit > 1
          AND retry_count < retry_limit;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN cur;

    read_loop: LOOP
        FETCH cur INTO task_id, task_retry_count, task_updated_at;
        IF done THEN
            LEAVE read_loop;
        END IF;

        SET backoff_time = LEAST(POWER(2, task_retry_count) * {DB_SETUP_BACKOFF_MULTIPLIER_SECONDS}, {DB_SETUP_BACKOFF_MAX_SECONDS});

        IF TIMESTAMPDIFF(SECOND, task_updated_at, CURRENT_TIMESTAMP) > backoff_time THEN
            -- Reopen the task
            UPDATE bountyboard
            SET status = 'PENDING',
                retry_count = retry_count + 1,
                updated_at = CURRENT_TIMESTAMP,
                worker_id = NULL
            WHERE id = task_id;

            INSERT INTO logs (message) VALUES (CONCAT('Task ', task_id, ' reopened for retry. Retry count: ', task_retry_count + 1, '. Backoff time: ', backoff_time, ' seconds.'));
        END IF;
    END LOOP;
    CLOSE cur;
END;
