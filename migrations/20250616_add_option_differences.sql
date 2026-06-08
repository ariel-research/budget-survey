-- Migration: Add option differences columns for cyclic shift strategy
-- Date: 2025-06-16
-- Description: Add option1_differences and option2_differences columns to comparison_pairs table
--              to support displaying vector differences in cyclic shift strategy

-- Add the new columns for storing difference vectors
ALTER TABLE `comparison_pairs` 
ADD COLUMN `option1_differences` JSON DEFAULT NULL AFTER `option2_strategy`,
ADD COLUMN `option2_differences` JSON DEFAULT NULL AFTER `option1_differences`;

-- Add comment to document the purpose of these columns
ALTER TABLE `comparison_pairs` 
COMMENT = 'Stores comparison pairs for surveys. option1_differences and option2_differences store vector changes for cyclic shift strategy.'; 