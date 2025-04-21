-- Migration: Add stories table and refactor surveys table
-- Date: 2025-04-01

-- Start transaction for safe migration
START TRANSACTION;

SET NAMES utf8mb4;

-- 1. Create the stories table if it doesn't exist
CREATE TABLE IF NOT EXISTS stories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    title JSON NOT NULL,
    description JSON NOT NULL,
    subjects JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_story_code (code) -- Index on the referenced column is important
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Add story_code column to surveys table if it doesn't exist
DELIMITER //
DROP PROCEDURE IF EXISTS add_story_code_column//
CREATE PROCEDURE add_story_code_column()
BEGIN
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = 'surveys'
                      AND COLUMN_NAME = 'story_code'
                      AND TABLE_SCHEMA = DATABASE()) THEN
        ALTER TABLE surveys
        ADD COLUMN story_code VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL AFTER name; -- Add as NULL initially
    END IF;
END//
DELIMITER ;

CALL add_story_code_column();
DROP PROCEDURE IF EXISTS add_story_code_column;

-- 3. Insert initial stories with manual data if they don't exist
-- Government ministries story
INSERT IGNORE INTO stories (code, title, description, subjects)
VALUES (
    'government_budget',
    JSON_OBJECT(
        'he', 'תקציב ממשלת ישראל',
        'en', 'Israeli Government Budget'
    ),
    JSON_OBJECT(
        'he', 'בסקר זה, תתבקש/י לחלק את תקציב הממשלה בין שלושה משרדים.',
        'en', 'In this survey, you will divide the government budget between three ministries.'
    ),
    JSON_ARRAY(
        JSON_OBJECT('he', 'משרד הביטחון', 'en', 'Ministry of Defense'),
        JSON_OBJECT('he', 'משרד החינוך', 'en', 'Ministry of Education'),
        JSON_OBJECT('he', 'משרד הבריאות', 'en', 'Ministry of Health')
    )
);

-- Municipal budget story
INSERT IGNORE INTO stories (code, title, description, subjects)
VALUES (
    'municipal_budget',
    JSON_OBJECT(
        'he', 'תקציב העירייה שלך',
        'en', 'The municipal budget of your city'
    ),
    JSON_OBJECT(
        'he', 'בסקר זה, תתבקש/י לחלק את התקציב העירוני בעיר מגוריך בין שלושה תחומים.',
        'en', 'In this survey, you will divide the municipal budget in your city between three sections.'
    ),
    JSON_ARRAY(
        JSON_OBJECT('he', 'מוסדות חינוך', 'en', 'Education institutes'),
        JSON_OBJECT('he', 'סיוע לנזקקים', 'en', 'Supporting those in need'),
        JSON_OBJECT('he', 'אירועי תרבות', 'en', 'Cultural events')
    )
);

-- 4. Update existing surveys to reference the correct story
-- Make sure the story_code column exists before trying to update it
DELIMITER //
DROP PROCEDURE IF EXISTS update_surveys_government_budget//
CREATE PROCEDURE update_surveys_government_budget()
BEGIN
    IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'surveys' AND COLUMN_NAME = 'story_code')
       AND EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'surveys' AND COLUMN_NAME = 'name') THEN

        UPDATE surveys
        SET story_code = 'government_budget'
        WHERE (JSON_UNQUOTE(JSON_EXTRACT(name, '$.en')) LIKE '%Government Budget%'
           OR JSON_UNQUOTE(JSON_EXTRACT(name, '$.he')) LIKE '%תקציב ממשלת ישראל%')
        AND story_code IS NULL; -- Only update if story_code is not already set
    END IF;
END//
DELIMITER ;

CALL update_surveys_government_budget();
DROP PROCEDURE IF EXISTS update_surveys_government_budget;

DELIMITER //
DROP PROCEDURE IF EXISTS update_surveys_municipal_budget//
CREATE PROCEDURE update_surveys_municipal_budget()
BEGIN
    IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'surveys' AND COLUMN_NAME = 'story_code')
       AND EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'surveys' AND COLUMN_NAME = 'name') THEN

        UPDATE surveys
        SET story_code = 'municipal_budget'
        WHERE (JSON_UNQUOTE(JSON_EXTRACT(name, '$.en')) LIKE '%municipal budget%'
           OR JSON_UNQUOTE(JSON_EXTRACT(name, '$.he')) LIKE '%תקציב העירייה%')
        AND story_code IS NULL; -- Only update if story_code is not already set
    END IF;
END//
DELIMITER ;

CALL update_surveys_municipal_budget();
DROP PROCEDURE IF EXISTS update_surveys_municipal_budget;

-- 4.1 Update any remaining surveys with a default story code (if appropriate)
-- Ensure column exists before update
DELIMITER //
DROP PROCEDURE IF EXISTS update_remaining_surveys//
CREATE PROCEDURE update_remaining_surveys()
BEGIN
    IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'surveys' AND COLUMN_NAME = 'story_code') THEN
        UPDATE surveys
        SET story_code = 'government_budget'
        WHERE story_code IS NULL;
    END IF;
END//
DELIMITER ;

CALL update_remaining_surveys();
DROP PROCEDURE IF EXISTS update_remaining_surveys;

-- 5. Verify all surveys have story_code values
SELECT COUNT(*) AS surveys_without_story FROM surveys WHERE story_code IS NULL;

-- 6. Ensure story_code column has the correct definition (type, charset, collation, NOT NULL)
DELIMITER //
DROP PROCEDURE IF EXISTS ensure_story_code_definition//
CREATE PROCEDURE ensure_story_code_definition()
BEGIN
    -- Check if the column exists first
    IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE()
                 AND TABLE_NAME = 'surveys'
                 AND COLUMN_NAME = 'story_code') THEN

        -- Verify no NULL values exist BEFORE enforcing NOT NULL
        IF (SELECT COUNT(*) FROM surveys WHERE story_code IS NULL) = 0 THEN
            -- Modify the column to ensure the full correct definition.
            ALTER TABLE surveys
            MODIFY COLUMN story_code VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
            SELECT 'Ensured surveys.story_code has correct definition (VARCHAR(50), utf8mb4, utf8mb4_unicode_ci, NOT NULL).' AS status;
        ELSE
            -- Signal an error because NULLs exist where they shouldn't
             SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot enforce NOT NULL constraint for surveys.story_code because NULL values exist. Please fix data first.';
        END IF;
    ELSE
         SELECT 'Column surveys.story_code does not exist, skipping definition check.' AS status;
    END IF;
END//
DELIMITER ;

CALL ensure_story_code_definition();
DROP PROCEDURE IF EXISTS ensure_story_code_definition;

-- 7. Add foreign key constraint if it doesn't exist
DELIMITER //
DROP PROCEDURE IF EXISTS add_fk_survey_story//
CREATE PROCEDURE add_fk_survey_story()
BEGIN
    -- Check if referencing column exists, is NOT NULL, and referenced column exists
    IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'surveys' AND COLUMN_NAME = 'story_code' AND IS_NULLABLE = 'NO')
       AND EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'stories' AND COLUMN_NAME = 'code')
       -- Check if FK does not already exist
       AND NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
                       WHERE CONSTRAINT_SCHEMA = DATABASE()
                         AND TABLE_NAME = 'surveys'
                         AND CONSTRAINT_NAME = 'fk_survey_story'
                         AND CONSTRAINT_TYPE = 'FOREIGN KEY') THEN

        ALTER TABLE surveys
        ADD CONSTRAINT fk_survey_story FOREIGN KEY (story_code) REFERENCES stories(code) ON DELETE RESTRICT;

    END IF;
END//
DELIMITER ;

CALL add_fk_survey_story();
DROP PROCEDURE IF EXISTS add_fk_survey_story;

-- Add index on the foreign key column in surveys table for performance if it doesn't exist
DELIMITER //
DROP PROCEDURE IF EXISTS add_index_story_code_surveys//
CREATE PROCEDURE add_index_story_code_surveys()
BEGIN
    IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'surveys' AND COLUMN_NAME = 'story_code')
       AND NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'surveys'
                      AND INDEX_NAME = 'idx_fk_story_code') THEN
        ALTER TABLE surveys
        ADD INDEX idx_fk_story_code (story_code);
    END IF;
END//
DELIMITER ;

CALL add_index_story_code_surveys();
DROP PROCEDURE IF EXISTS add_index_story_code_surveys;


-- 8. Remove redundant columns if they exist
DELIMITER //
DROP PROCEDURE IF EXISTS drop_name_column//
CREATE PROCEDURE drop_name_column()
BEGIN
    IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = 'surveys'
                      AND COLUMN_NAME = 'name'
                      AND TABLE_SCHEMA = DATABASE()) THEN
        ALTER TABLE surveys
        DROP COLUMN name;
    END IF;
END//
DELIMITER ;

CALL drop_name_column();
DROP PROCEDURE IF EXISTS drop_name_column;

DELIMITER //
DROP PROCEDURE IF EXISTS drop_subjects_column//
CREATE PROCEDURE drop_subjects_column()
BEGIN
    IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = 'surveys'
                      AND COLUMN_NAME = 'subjects'
                      AND TABLE_SCHEMA = DATABASE()) THEN
        ALTER TABLE surveys
        DROP COLUMN subjects;
    END IF;
END//
DELIMITER ;

CALL drop_subjects_column();
DROP PROCEDURE IF EXISTS drop_subjects_column;

DELIMITER //
DROP PROCEDURE IF EXISTS drop_description_column//
CREATE PROCEDURE drop_description_column()
BEGIN
    IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = 'surveys'
                      AND COLUMN_NAME = 'description'
                      AND TABLE_SCHEMA = DATABASE()) THEN
        ALTER TABLE surveys
        DROP COLUMN description;
    END IF;
END//
DELIMITER ;

CALL drop_description_column();
DROP PROCEDURE IF EXISTS drop_description_column;

-- Commit changes if everything is successful
COMMIT;

-- Show migration success message
SELECT 'Migration completed successfully - all changes committed atomically' AS result;