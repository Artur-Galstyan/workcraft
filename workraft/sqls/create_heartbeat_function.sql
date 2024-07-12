CREATE OR REPLACE FUNCTION heartbeat(in_worker_id UUID) RETURNS void AS $$
BEGIN
    UPDATE peon
    SET last_heartbeat = NOW()
    WHERE id = in_worker_id;
END;
$$ LANGUAGE plpgsql;
