-- Migration: Add uniqueness constraint to prevent duplicate survey responses
-- Date: 2025-12-04
-- Description: Ensures each user can only have one response per survey
--              Prevents duplicate entries from browser back button or multiple submissions

-- Step 1: Delete duplicate responses, keeping only the most recent one per user-survey combination
-- Use a temp table to work around MySQL's limitation on deleting from same table in subquery
CREATE TEMPORARY TABLE temp_keep_ids AS
SELECT MAX(id) as id
FROM `survey_responses`
GROUP BY user_id, survey_id;

DELETE FROM `survey_responses`
WHERE id NOT IN (SELECT id FROM temp_keep_ids);

DROP TEMPORARY TABLE temp_keep_ids;

-- Step 2: Add unique constraint on (user_id, survey_id)
-- Check if constraint already exists before adding
ALTER TABLE `survey_responses`
ADD CONSTRAINT `uq_user_survey` UNIQUE KEY `unique_user_survey` (`user_id`, `survey_id`);

