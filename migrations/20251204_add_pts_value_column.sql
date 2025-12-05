-- Migration: Add pts_value column for early awareness failure tracking
-- Date: 2025-12-04
-- Description: Adds pts_value column to survey_responses table to track
--              which awareness check failed (PTS=7 for first, PTS=10 for second)

ALTER TABLE `survey_responses`
ADD COLUMN `pts_value` INT DEFAULT NULL
COMMENT 'Panel4All PTS value for early awareness failures (7=first, 10=second)';

