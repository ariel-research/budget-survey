-- Migration: Add per-survey awareness PTS tokens and update awareness codes
-- Date: 2025-12-09
-- Description:
--   * Adds awareness_pts JSON column to surveys to store per-survey PTS tokens
--   * Seeds tokens for surveys 116 and 117
--   * Clarifies survey_responses.pts_value semantics to store awareness failure codes

ALTER TABLE `surveys`
ADD COLUMN `awareness_pts` JSON DEFAULT NULL
AFTER `pair_generation_config`;

-- Seed known tokens
UPDATE `surveys`
SET `awareness_pts` = JSON_OBJECT(
    'first', 'UFWGYNtT9GZiK7M7EZJjPw==',
    'second', '0PiK9ZYVZtvXH0FYjxQJlQ=='
)
WHERE `id` = 116;

UPDATE `surveys`
SET `awareness_pts` = JSON_OBJECT(
    'first', 'Qk5FKZWQ1F2z3Sib7DhUYg==',
    'second', '4AbOZdihYqHZtoXVrjz/rg=='
)
WHERE `id` = 117;

-- Store awareness failure code (1=first awareness, 2=second awareness)
ALTER TABLE `survey_responses`
MODIFY COLUMN `pts_value` INT DEFAULT NULL
COMMENT 'Awareness failure code (1=first awareness, 2=second awareness)';

