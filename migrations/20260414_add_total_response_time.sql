-- Migration: Add total_response_time_seconds to survey_responses table
-- Description: Tracks the total cognitive load (time in seconds) a user spends on the survey page.

ALTER TABLE `survey_responses`
ADD COLUMN `total_response_time_seconds` FLOAT DEFAULT NULL COMMENT 'Total time spent on the survey page in seconds';
