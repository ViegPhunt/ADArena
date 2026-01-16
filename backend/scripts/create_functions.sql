-- Calculate score changes when a flag is captured
-- Uses logistic function based on current scores of attacker and victim
-- Locks rows in order (lower team_id first) to prevent deadlocks
CREATE OR REPLACE FUNCTION recalculate_rating(
    _attacker_id INTEGER,
    _victim_id INTEGER,
    _task_id INTEGER,
    _flag_id INTEGER
)
RETURNS TABLE (
    attacker_delta FLOAT,
    victim_delta FLOAT
)
AS $$
DECLARE
    hardness        FLOAT;   -- Game difficulty multiplier
    inflate         BOOLEAN; -- If true: attacker gain can exceed victim loss
    scale           FLOAT;
    norm            FLOAT;
    attacker_score  FLOAT;
    victim_score    FLOAT;
    _attacker_delta FLOAT;
    _victim_delta   FLOAT;
BEGIN
    -- Get game config
    SELECT game_hardness, inflation 
    FROM GameConfig 
    WHERE id = 1 
    INTO hardness, inflate;

    -- Lock rows in consistent order to prevent deadlocks
    IF _attacker_id < _victim_id THEN
        SELECT score FROM TeamTasks
        WHERE team_id = _attacker_id AND task_id = _task_id
        FOR NO KEY UPDATE
        INTO attacker_score;

        SELECT score FROM TeamTasks
        WHERE team_id = _victim_id AND task_id = _task_id
        FOR NO KEY UPDATE
        INTO victim_score;
    ELSE
        SELECT score FROM TeamTasks
        WHERE team_id = _victim_id AND task_id = _task_id
        FOR NO KEY UPDATE
        INTO victim_score;

        SELECT score FROM TeamTasks
        WHERE team_id = _attacker_id AND task_id = _task_id
        FOR NO KEY UPDATE
        INTO attacker_score;
    END IF;

    -- Calculate score deltas using logistic function
    scale := 50 * sqrt(hardness);
    norm := ln(ln(hardness)) / 12;
    _attacker_delta := scale / (1 + exp((sqrt(attacker_score) - sqrt(victim_score)) * norm));
    _victim_delta := -least(victim_score, _attacker_delta);  -- Prevent negative scores

    -- Zero-sum mode: cap attacker gain to victim loss
    IF NOT inflate THEN
        _attacker_delta := least(_attacker_delta, -_victim_delta);
    END IF;

    -- Record stolen flag
    INSERT INTO StolenFlags (attacker_id, flag_id) 
    VALUES (_attacker_id, _flag_id);

    -- Update attacker stats
    UPDATE TeamTasks
    SET stolen = stolen + 1,
        score = score + _attacker_delta
    WHERE team_id = _attacker_id AND task_id = _task_id;

    -- Update victim stats
    UPDATE TeamTasks
    SET lost = lost + 1,
        score = score + _victim_delta
    WHERE team_id = _victim_id AND task_id = _task_id;

    RETURN QUERY SELECT _attacker_delta, _victim_delta;
END;
$$ LANGUAGE plpgsql;


-- Get first successful attack for each service vulnerability
-- Returns one row per (task_id, vuln_number) combination
CREATE OR REPLACE FUNCTION get_first_bloods()
RETURNS TABLE (
    submit_time     TIMESTAMP WITH TIME ZONE,
    attacker_name   VARCHAR(255),
    task_name       VARCHAR(255),
    attacker_id     INTEGER,
    victim_id       INTEGER,
    task_id         INTEGER,
    vuln_number     INTEGER
)
AS $$
BEGIN
    RETURN QUERY 
    SELECT DISTINCT ON (f.task_id, f.vuln_number)
        sf.submit_time,
        tm.name AS attacker_name,
        tk.name AS task_name,
        sf.attacker_id,
        f.team_id AS victim_id,
        f.task_id,
        f.vuln_number
    FROM StolenFlags sf
    JOIN Flags f ON f.id = sf.flag_id
    JOIN Teams tm ON tm.id = sf.attacker_id
    JOIN Tasks tk ON tk.id = f.task_id
    ORDER BY f.task_id, f.vuln_number, sf.submit_time;
END;
$$ LANGUAGE plpgsql STABLE;


-- Initialize TeamTasks with all team-task combinations
-- Safe to call multiple times (skips existing records)
CREATE OR REPLACE FUNCTION fix_teamtasks()
RETURNS VOID
AS $$
BEGIN
    INSERT INTO TeamTasks (task_id, team_id, status, score)
    SELECT 
        tasks.id AS task_id,
        teams.id AS team_id,
        -1 AS status,              -- Not checked yet
        tasks.default_score AS score
    FROM teams
    CROSS JOIN tasks
    ON CONFLICT (task_id, team_id) DO NOTHING;
END;
$$ LANGUAGE plpgsql;