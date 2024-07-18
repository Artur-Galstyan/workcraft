
-- This function sets all FAILED tasks to PENDING
-- based on the retry_on_failure and retry_count and retry_limit
-- columns in the bountyboard table
-- this function will also first check if the delay
-- based on exponential backoff has passed

CREATE OR REPLACE FUNCTION reopen_failed_tasks() RETURNS INTEGER AS $$
DECLARE
    tasks_reopened INTEGER := 0;
    task RECORD;
BEGIN
    FOR task IN
        SELECT * FROM bountyboard
        WHERE status = 'FAILURE'
          AND retry_on_failure = true
          AND retry_limit > 1
          AND retry_count < retry_limit
    LOOP
        -- Calculate backoff time (in seconds)
        -- Using 2^retry_count * 60 seconds, capped at 1 hour
        DECLARE
            backoff_time INTEGER := LEAST(POWER(2, task.retry_count) * 60, 3600);
        BEGIN
            RAISE NOTICE 'Task % backoff time: % seconds', task.id, backoff_time;
            -- Check if enough time has passed since the last update
            IF (CURRENT_TIMESTAMP - task.updated_at) > (backoff_time * INTERVAL '1 second') THEN

                -- Reopen the task
                UPDATE bountyboard
                SET status = 'PENDING',
                    retry_count = retry_count + 1,
                    updated_at = CURRENT_TIMESTAMP,
                    worker_id = NULL
                WHERE id = task.id;

                tasks_reopened := tasks_reopened + 1;
            END IF;
        END;
    END LOOP;

    RETURN tasks_reopened;
END;
$$ LANGUAGE plpgsql;
