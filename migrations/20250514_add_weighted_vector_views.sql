-- Migration: 20250514_add_weighted_vector_views.sql
-- Creates views for analyzing user preferences for weighted vector strategies

-- View 1: Users preferring weighted average vectors
CREATE OR REPLACE VIEW v_users_preferring_weighted_vectors AS
SELECT 
    sr.user_id,
    sr.survey_id,
    s.story_code,
    JSON_UNQUOTE(JSON_EXTRACT(s.pair_generation_config, '$.strategy')) AS survey_strategy,
    COUNT(cp.id) AS total_pairs,
    SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END) AS weighted_choices,
    sr.created_at AS response_date
FROM 
    survey_responses sr
JOIN 
    surveys s ON sr.survey_id = s.id
JOIN 
    comparison_pairs cp ON sr.id = cp.survey_response_id
WHERE 
    sr.completed = TRUE  
    AND sr.attention_check_failed = FALSE
    AND JSON_EXTRACT(s.pair_generation_config, '$.strategy') = 'single_peaked_preference_test'
GROUP BY 
    sr.user_id, sr.survey_id, s.story_code, 
    JSON_UNQUOTE(JSON_EXTRACT(s.pair_generation_config, '$.strategy')),
    sr.created_at
HAVING 
    COUNT(cp.id) = SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END);

-- View 2: Users preferring rounded weighted average vectors
CREATE OR REPLACE VIEW v_users_preferring_rounded_weighted_vectors AS
SELECT 
    sr.user_id,
    sr.survey_id,
    s.story_code,
    JSON_UNQUOTE(JSON_EXTRACT(s.pair_generation_config, '$.strategy')) AS survey_strategy,
    COUNT(cp.id) AS total_pairs,
    SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END) AS weighted_choices,
    sr.created_at AS response_date
FROM 
    survey_responses sr
JOIN 
    surveys s ON sr.survey_id = s.id
JOIN 
    comparison_pairs cp ON sr.id = cp.survey_response_id
WHERE 
    sr.completed = TRUE  
    AND sr.attention_check_failed = FALSE
    AND JSON_EXTRACT(s.pair_generation_config, '$.strategy') = 'single_peaked_preference_test_rounded'
GROUP BY 
    sr.user_id, sr.survey_id, s.story_code, 
    JSON_UNQUOTE(JSON_EXTRACT(s.pair_generation_config, '$.strategy')),
    sr.created_at
HAVING 
    COUNT(cp.id) = SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END);

-- View 3: Users preferring any type of weighted vectors
CREATE OR REPLACE VIEW v_users_preferring_any_weighted_vectors AS
SELECT 
    sr.user_id,
    sr.survey_id,
    s.story_code,
    JSON_UNQUOTE(JSON_EXTRACT(s.pair_generation_config, '$.strategy')) AS survey_strategy,
    COUNT(cp.id) AS total_pairs,
    SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END) AS weighted_choices,
    sr.created_at AS response_date
FROM 
    survey_responses sr
JOIN 
    surveys s ON sr.survey_id = s.id
JOIN 
    comparison_pairs cp ON sr.id = cp.survey_response_id
WHERE 
    sr.completed = TRUE  
    AND sr.attention_check_failed = FALSE
    AND JSON_EXTRACT(s.pair_generation_config, '$.strategy') IN ('single_peaked_preference_test', 'single_peaked_preference_test_rounded')
GROUP BY 
    sr.user_id, sr.survey_id, s.story_code, 
    JSON_UNQUOTE(JSON_EXTRACT(s.pair_generation_config, '$.strategy')),
    sr.created_at
HAVING 
    COUNT(cp.id) = SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END);
