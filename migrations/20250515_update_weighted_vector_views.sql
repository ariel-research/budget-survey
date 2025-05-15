-- Migration: 20250515_update_weighted_vector_views.sql
-- Updates views for analyzing user preferences for weighted vector strategies
-- Makes the criteria more realistic by changing from requiring 100% preference
-- to requiring majority preference (>50%)

-- Update View 1: Users preferring weighted average vectors (majority criteria)
DROP VIEW IF EXISTS v_users_preferring_weighted_vectors;
CREATE VIEW v_users_preferring_weighted_vectors AS
SELECT 
    sr.user_id,
    sr.survey_id,
    s.story_code,
    JSON_UNQUOTE(JSON_EXTRACT(s.pair_generation_config, '$.strategy')) AS survey_strategy,
    COUNT(cp.id) AS total_pairs,
    SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END) AS weighted_choices,
    ROUND(SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(cp.id)) AS preference_percentage,
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
    AND JSON_EXTRACT(s.pair_generation_config, '$.strategy') = 'weighted_average_vector'
GROUP BY 
    sr.user_id, sr.survey_id, s.story_code, 
    JSON_UNQUOTE(JSON_EXTRACT(s.pair_generation_config, '$.strategy')),
    sr.created_at
HAVING 
    SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END) > COUNT(cp.id) / 2;

-- Update View 2: Users preferring rounded weighted average vectors (majority criteria)
DROP VIEW IF EXISTS v_users_preferring_rounded_weighted_vectors;
CREATE VIEW v_users_preferring_rounded_weighted_vectors AS
SELECT 
    sr.user_id,
    sr.survey_id,
    s.story_code,
    JSON_UNQUOTE(JSON_EXTRACT(s.pair_generation_config, '$.strategy')) AS survey_strategy,
    COUNT(cp.id) AS total_pairs,
    SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END) AS weighted_choices,
    ROUND(SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(cp.id)) AS preference_percentage,
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
    AND JSON_EXTRACT(s.pair_generation_config, '$.strategy') = 'rounded_weighted_average_vector'
GROUP BY 
    sr.user_id, sr.survey_id, s.story_code, 
    JSON_UNQUOTE(JSON_EXTRACT(s.pair_generation_config, '$.strategy')),
    sr.created_at
HAVING 
    SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END) > COUNT(cp.id) / 2;

-- Update View 3: Users preferring any type of weighted vectors (majority criteria)
DROP VIEW IF EXISTS v_users_preferring_any_weighted_vectors;
CREATE VIEW v_users_preferring_any_weighted_vectors AS
SELECT 
    sr.user_id,
    sr.survey_id,
    s.story_code,
    JSON_UNQUOTE(JSON_EXTRACT(s.pair_generation_config, '$.strategy')) AS survey_strategy,
    COUNT(cp.id) AS total_pairs,
    SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END) AS weighted_choices,
    ROUND(SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(cp.id)) AS preference_percentage,
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
    AND JSON_EXTRACT(s.pair_generation_config, '$.strategy') IN ('weighted_average_vector', 'rounded_weighted_average_vector')
GROUP BY 
    sr.user_id, sr.survey_id, s.story_code, 
    JSON_UNQUOTE(JSON_EXTRACT(s.pair_generation_config, '$.strategy')),
    sr.created_at
HAVING 
    SUM(CASE WHEN cp.user_choice = 2 THEN 1 ELSE 0 END) > COUNT(cp.id) / 2; 