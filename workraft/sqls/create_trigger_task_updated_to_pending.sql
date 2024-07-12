CREATE TRIGGER task_updated_to_pending_trigger
AFTER UPDATE ON bountyboard
FOR EACH ROW
WHEN (OLD.status != 'PENDING' AND NEW.status = 'PENDING')
EXECUTE FUNCTION notify_new_task();
