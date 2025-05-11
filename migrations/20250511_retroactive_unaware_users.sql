-- Migration: 20250511_retroactive_unaware_users.sql
-- Purpose: Retroactively blacklist users who failed attention checks but weren't blacklisted

SET @current_timestamp = NOW();

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

-- Log the number of users found
SELECT CONCAT('Found ', COUNT(*), ' users to blacklist') AS log_message
FROM tmp_users_to_blacklist;

-- Create a table with the earliest failure for each user
DROP TEMPORARY TABLE IF EXISTS tmp_earliest_failures;
CREATE TEMPORARY TABLE tmp_earliest_failures (
    user_id VARCHAR(128),
    failed_survey_id INT,
    first_failure TIMESTAMP
);

-- First find earliest failure date for each user
DROP TEMPORARY TABLE IF EXISTS tmp_earliest_failures;
CREATE TEMPORARY TABLE tmp_earliest_failures AS
SELECT user_id, MIN(created_at) AS first_failure
FROM tmp_users_to_blacklist
GROUP BY user_id;

-- Then join back to get the survey_id that corresponds to that earliest date
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
    CONCAT('Blacklisted ', ROW_COUNT(), ' users retroactively') AS execution_result;

-- Clean up
DROP TEMPORARY TABLE IF EXISTS tmp_users_to_blacklist;
DROP TEMPORARY TABLE IF EXISTS tmp_earliest_failures; 