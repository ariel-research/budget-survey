-- Migration: Add pair instructions to pair_generation_config
-- Date: 2025-09-07
-- Description: Add pair_instructions field to existing temporal_preference_test surveys' pair_generation_config

-- Update existing temporal_preference_test surveys to include default instructions in pair_generation_config
UPDATE `surveys`
SET `pair_generation_config` = JSON_SET(
    `pair_generation_config`,
    '$.pair_instructions',
    JSON_OBJECT(
        'he', 'עליכם לקבוע את התקציב עבור שתי שנים עוקבות: השנה הנוכחית, והשנה הבאה. איזה מבין שני התקציבים הבאים תעדיפו שיהיה התקציב בשנה הנוכחית? התקציב שלא תבחרו יהיה התקציב בשנה הבאה.',
        'en', 'You need to set the budget for two consecutive years: the current year and next year. Which of the following two budgets would you prefer to be the current year''s budget? The budget you don''t choose will be next year''s budget.'
    )
)
WHERE JSON_EXTRACT(`pair_generation_config`, '$.strategy') = 'temporal_preference_test';
