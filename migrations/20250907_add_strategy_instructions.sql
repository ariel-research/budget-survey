-- Migration: Add pair instructions to pair_generation_config
-- Date: 2025-09-07
-- Description: Add pair_instructions field to existing biennial_budget_preference surveys' pair_generation_config

-- Update existing biennial_budget_preference surveys to include default instructions in pair_generation_config
UPDATE `surveys`
SET `pair_generation_config` = JSON_SET(
    `pair_generation_config`,
    '$.pair_instructions',
    JSON_OBJECT(
        'he', 'עליכם לקבוע את התקציב עבור <strong>שתי שנים עוקבות</strong>: השנה הנוכחית, והשנה הבאה. איזה מבין שני התקציבים הבאים תעדיפו שיהיה התקציב <strong>בשנה הנוכחית</strong>? התקציב שלא תבחרו יהיה התקציב <strong>בשנה הבאה</strong>.',
        'en', 'You need to set the budget for <strong>two consecutive years</strong>: <strong>the current year</strong> and <strong>next year</strong>. Which of the following two budgets would you prefer to be <strong>the current year''s budget</strong>? The budget you don''t choose will be <strong>next year''s budget</strong>.'
    )
)
WHERE JSON_EXTRACT(`pair_generation_config`, '$.strategy') = 'biennial_budget_preference';
