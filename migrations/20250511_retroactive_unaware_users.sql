-- Migration: 20250511_retroactive_unaware_users.sql
-- Purpose: Retroactively blacklist users who failed attention checks but weren't blacklisted

-- Start transaction for safety
START TRANSACTION;

-- Create a temporary table to hold users who should be blacklisted
DROP TEMPORARY TABLE IF EXISTS tmp_users_to_blacklist;
CREATE TEMPORARY TABLE tmp_users_to_blacklist (
    user_id VARCHAR(128),
    survey_id INT,
    created_at TIMESTAMP
);

-- Find users with failed attention checks who aren't already blacklisted
INSERT INTO tmp_users_to_blacklist (user_id, survey_id, created_at)
SELECT 
    sr.user_id,
    sr.survey_id,
    sr.created_at
FROM 
    survey_responses sr
JOIN 
    users u ON sr.user_id = u.id
WHERE 
    sr.attention_check_failed = TRUE
    AND u.blacklisted = FALSE
ORDER BY 
    sr.created_at ASC;

-- Log both failures and unique users
SELECT 
    CONCAT('Found ', COUNT(*), ' failed attention checks across ', 
           COUNT(DISTINCT user_id), ' unique users') AS log_message
FROM tmp_users_to_blacklist;

-- Show stats on users with multiple failures
SELECT 
    CONCAT('Users with multiple failures: ', 
           SUM(CASE WHEN failure_count > 1 THEN 1 ELSE 0 END),
           ' (', SUM(failure_count - 1), ' additional failures beyond first)') 
    AS multi_failure_stats
FROM (
    SELECT user_id, COUNT(*) AS failure_count
    FROM tmp_users_to_blacklist
    GROUP BY user_id
    HAVING COUNT(*) > 1
) multi_fails;

-- Find earliest failure date for each user
DROP TEMPORARY TABLE IF EXISTS tmp_earliest_failures;
CREATE TEMPORARY TABLE tmp_earliest_failures AS
SELECT user_id, MIN(created_at) AS first_failure
FROM tmp_users_to_blacklist
GROUP BY user_id;

-- Join back to get the survey_id that corresponds to that earliest date
UPDATE users u
JOIN (
    SELECT t1.user_id, t1.survey_id AS failed_survey_id, t1.created_at
    FROM tmp_users_to_blacklist t1
    JOIN tmp_earliest_failures t2 
        ON t1.user_id = t2.user_id AND t1.created_at = t2.first_failure
) AS t ON u.id = t.user_id
SET 
    u.blacklisted = TRUE,
    u.blacklisted_at = t.created_at,
    u.failed_survey_id = t.failed_survey_id;

-- Report results
SELECT 
    CONCAT('Blacklisted ', ROW_COUNT(), ' users based on their earliest failed attention check') 
    AS execution_result;

-- Clean up
DROP TEMPORARY TABLE IF EXISTS tmp_users_to_blacklist;
DROP TEMPORARY TABLE IF EXISTS tmp_earliest_failures;

-- Commit the transaction
COMMIT;
