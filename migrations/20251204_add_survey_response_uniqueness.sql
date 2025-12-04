-- Migration: Add uniqueness constraint to prevent duplicate survey responses
-- Date: 2025-12-04
-- Description: Ensures each user can only have one response per survey
--              Prevents duplicate entries from browser back button or multiple submissions

-- Add unique constraint on (user_id, survey_id)
ALTER TABLE `survey_responses`
ADD CONSTRAINT `uq_user_survey` UNIQUE KEY `unique_user_survey` (`user_id`, `survey_id`);

