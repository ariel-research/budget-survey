-- Migration: Add User Blacklist Columns
-- Date: 2025-05-01

-- Add blacklist columns to users table
ALTER TABLE `users` 
  ADD COLUMN `blacklisted` BOOLEAN DEFAULT FALSE,
  ADD COLUMN `blacklisted_at` TIMESTAMP NULL,
  ADD COLUMN `failed_survey_id` INT NULL,
  ADD INDEX `idx_blacklisted` (`blacklisted`);

-- Add foreign key constraint for failed_survey_id referencing surveys.id
ALTER TABLE `users`
  ADD CONSTRAINT `fk_failed_survey` 
  FOREIGN KEY (`failed_survey_id`) REFERENCES `surveys` (`id`) 
  ON DELETE SET NULL;

-- Documentation:
-- - blacklisted: Flag indicating if user is blacklisted from taking surveys
-- - blacklisted_at: Timestamp when user was blacklisted
-- - failed_survey_id: ID of the survey where user failed attention checks
-- - idx_blacklisted: Index for faster lookups of blacklisted users 