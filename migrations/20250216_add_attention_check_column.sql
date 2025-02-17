-- UP Migration
ALTER TABLE survey_responses
ADD COLUMN attention_check_failed BOOLEAN DEFAULT FALSE AFTER completed;
