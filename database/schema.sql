-- Database Schema for budget-survey
-- Reflects state AFTER migration 20250401_add_stories_table.sql
-- 20250501_add_user_blacklist.sql

-- WARNING! Running this script will DROP existing tables
-- (users, stories, surveys, survey_responses, comparison_pairs)
-- and ALL their data before recreating the schema.
-- DO NOT run this on a production database or any database
-- with data you want to keep. Use primarily for initial
-- setup or resetting a development environment.

SET NAMES utf8mb4;
SET TIME_ZONE='Asia/Jerusalem';

SET foreign_key_checks = 0; -- Disable checks during potential drops/creates

-- --------- Users Table ---------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` VARCHAR(128) NOT NULL PRIMARY KEY,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `blacklisted` BOOLEAN DEFAULT FALSE,
  `blacklisted_at` TIMESTAMP NULL,
  `failed_survey_id` INT NULL,
  INDEX `idx_blacklisted` (`blacklisted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- --------- Stories Table ---------
DROP TABLE IF EXISTS `stories`;
CREATE TABLE `stories` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `code` VARCHAR(50) NOT NULL UNIQUE,
  `title` JSON NOT NULL,
  `description` JSON NOT NULL,
  `subjects` JSON NOT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX (`code`) -- Index for faster lookups & FK support
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- --------- Surveys Table ---------
DROP TABLE IF EXISTS `surveys`;
CREATE TABLE `surveys` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `story_code` VARCHAR(50) NOT NULL, -- FK to stories.code
  `active` BOOLEAN DEFAULT TRUE,
  `pair_generation_config` JSON NOT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX (`story_code`), -- Index for the foreign key
  FOREIGN KEY (`story_code`) REFERENCES `stories` (`code`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- --------- Survey Responses Table ---------
DROP TABLE IF EXISTS `survey_responses`;
CREATE TABLE `survey_responses` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` VARCHAR(128) NOT NULL, -- Should match users.id
  `survey_id` INT NOT NULL, -- Should match surveys.id
  `optimal_allocation` JSON NOT NULL,
  `user_comment` TEXT DEFAULT NULL,
  `completed` BOOLEAN DEFAULT FALSE,
  `attention_check_failed` BOOLEAN DEFAULT FALSE,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX (`user_id`), -- Index for potential joins/lookups
  INDEX (`survey_id`), -- Index for potential joins/lookups
  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT,
  FOREIGN KEY (`survey_id`) REFERENCES `surveys` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- --------- Comparison Pairs Table ---------
DROP TABLE IF EXISTS `comparison_pairs`;
CREATE TABLE `comparison_pairs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `survey_response_id` INT NOT NULL, -- FK to survey_responses.id
  `pair_number` INT NOT NULL,
  `option_1` JSON NOT NULL,
  `option_2` JSON NOT NULL,
  `user_choice` INT NOT NULL,
  `option1_strategy` VARCHAR(100) DEFAULT NULL,
  `option2_strategy` VARCHAR(100) DEFAULT NULL,
  `raw_user_choice` INT DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`survey_response_id`) REFERENCES `survey_responses` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Add foreign key constraint for users.failed_survey_id
ALTER TABLE `users`
  ADD CONSTRAINT `fk_failed_survey` 
  FOREIGN KEY (`failed_survey_id`) REFERENCES `surveys` (`id`) 
  ON DELETE SET NULL;


SET foreign_key_checks = 1; -- Re-enable checks