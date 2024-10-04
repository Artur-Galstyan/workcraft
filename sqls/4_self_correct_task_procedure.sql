CREATE PROCEDURE self_correct_tasks()
BEGIN
    DECLARE affected_count INT DEFAULT 0;
    DECLARE task_id CHAR(36);
    DECLARE task_queue VARCHAR(255);
    DECLARE done INT DEFAULT FALSE;
    DECLARE cur CURSOR FOR
        SELECT b.id, b.queue
        FROM bountyboard b
        LEFT JOIN peon p ON b.worker_id = p.id
        WHERE b.status = 'RUNNING'
        AND (p.id IS NULL OR p.status IN ('IDLE', 'OFFLINE') OR p.current_task != b.id);
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN cur;

    read_loop: LOOP
        FETCH cur INTO task_id, task_queue;
        IF done THEN
            LEAVE read_loop;
        END IF;

        SET affected_count = affected_count + 1;

        UPDATE bountyboard
        SET status = 'PENDING', worker_id = NULL, updated_at = CURRENT_TIMESTAMP
        WHERE id = task_id;

        INSERT INTO logs (message)
        VALUES (CONCAT('Task ', task_id, ' in queue ', task_queue, ' reset to PENDING.'));
    END LOOP;

    CLOSE cur;
END
