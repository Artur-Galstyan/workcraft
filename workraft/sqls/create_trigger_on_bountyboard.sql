DROP TRIGGER IF EXISTS task_inserted_trigger ON bountyboard;
CREATE TRIGGER task_inserted_trigger
AFTER INSERT ON bountyboard
FOR EACH ROW
WHEN (NEW.status = 'PENDING')
EXECUTE FUNCTION notify_new_task();
