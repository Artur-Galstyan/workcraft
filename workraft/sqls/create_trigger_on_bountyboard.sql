DROP TRIGGER IF EXISTS task_inserted_trigger ON bountyboard;
CREATE TRIGGER task_inserted_trigger
AFTER INSERT OR UPDATE OF status ON bountyboard
FOR EACH ROW
WHEN (NEW.status = 'PENDING')
EXECUTE FUNCTION notify_new_task();
