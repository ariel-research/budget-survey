-- Migration: Add stories table and refactor surveys table
-- Date: 2025-04-01

-- Start transaction for safe migration
START TRANSACTION;

-- 1. Create the stories table
CREATE TABLE stories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    title JSON NOT NULL,              
    description JSON NOT NULL,        
    subjects JSON NOT NULL,           
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_story_code (code)       
);

-- 2. Add story_code column to surveys table
ALTER TABLE surveys
ADD COLUMN story_code VARCHAR(50) AFTER name;

-- 3. Insert initial stories with manual data
-- Government ministries story
INSERT INTO stories (code, title, description, subjects)
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
INSERT INTO stories (code, title, description, subjects)
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
UPDATE surveys
SET story_code = 'government_budget'
WHERE JSON_UNQUOTE(JSON_EXTRACT(name, '$.en')) LIKE '%Government Budget%' 
   OR JSON_UNQUOTE(JSON_EXTRACT(name, '$.he')) LIKE '%תקציב ממשלת ישראל%';

UPDATE surveys
SET story_code = 'municipal_budget'
WHERE JSON_UNQUOTE(JSON_EXTRACT(name, '$.en')) LIKE '%municipal budget%'
   OR JSON_UNQUOTE(JSON_EXTRACT(name, '$.he')) LIKE '%תקציב העירייה%';

-- 5. Verify all surveys have story_code values
SELECT COUNT(*) AS surveys_without_story FROM surveys WHERE story_code IS NULL;

-- 6. Add NOT NULL constraint to story_code to ensure data integrity
ALTER TABLE surveys 
MODIFY COLUMN story_code VARCHAR(50) NOT NULL;

-- 7. Add foreign key constraint
ALTER TABLE surveys
ADD CONSTRAINT fk_survey_story FOREIGN KEY (story_code) REFERENCES stories(code) ON DELETE RESTRICT,
ADD INDEX idx_story_code (story_code);

-- 8. Remove redundant columns
ALTER TABLE surveys
DROP COLUMN name,
DROP COLUMN subjects;

-- Commit changes if everything is successful
COMMIT;