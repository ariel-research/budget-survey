-- Add unsuitable_for_strategy column to survey_responses table
ALTER TABLE `survey_responses`
ADD COLUMN `unsuitable_for_strategy` BOOLEAN DEFAULT FALSE COMMENT 'Indicates if user vector was unsuitable for pair generation strategy';

-- Add index for easier querying of unsuitable responses
CREATE INDEX `idx_unsuitable_strategy` ON `survey_responses` (`unsuitable_for_strategy`);

