-- Migration: Add transitivity analysis for extreme vectors strategy
-- Date: 2025-08-06
-- Description: Add transitivity_analysis column to survey_responses table

ALTER TABLE `survey_responses` 
ADD COLUMN `transitivity_analysis` JSON DEFAULT NULL 
COMMENT 'Transitivity metrics for extreme vector responses' 
AFTER `attention_check_failed`;

ALTER TABLE `survey_responses` 
ADD INDEX `idx_transitivity_analysis` ((CAST(transitivity_analysis AS CHAR(1)) COLLATE utf8mb4_bin));