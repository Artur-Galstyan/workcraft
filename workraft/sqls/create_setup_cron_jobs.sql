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
    IF NOT EXISTS (SELECT 1 FROM cron.job WHERE command = 'SELECT reopen_failed_tasks()') THEN
        PERFORM cron.schedule('* * * * *', 'SELECT reopen_failed_tasks()');
    END IF;
END $$;
