-- UP Migration
ALTER TABLE comparison_pairs
ADD COLUMN option1_strategy VARCHAR(100) AFTER user_choice,
ADD COLUMN option2_strategy VARCHAR(100) AFTER option1_strategy,
ADD COLUMN raw_user_choice INT NULL AFTER option2_strategy;