CREATE OR REPLACE FUNCTION notify_new_task() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO task_queue (task_id) VALUES (NEW.id);
    PERFORM pg_notify('new_task', NEW.id::text || '§' || NEW.queue);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
