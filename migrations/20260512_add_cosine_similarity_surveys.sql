-- Migration: Add cosine similarity rank-comparison surveys
-- Date: 2026-05-12

START TRANSACTION;

SET @cosine_story_code := COALESCE(
    (SELECT code FROM stories WHERE code = 'government_budget' LIMIT 1),
    (SELECT code FROM stories WHERE code = 'budget_2024' LIMIT 1),
    (SELECT code FROM stories ORDER BY code LIMIT 1)
);

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT
    @cosine_story_code,
    TRUE,
    '{"strategy": "cosine_similarity_vs_l1_rank_comparison", "params": {"num_pairs": 10}}'
WHERE @cosine_story_code IS NOT NULL
AND NOT EXISTS (
    SELECT 1
    FROM surveys
    WHERE JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l1_rank_comparison'
);

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT
    @cosine_story_code,
    TRUE,
    '{"strategy": "cosine_similarity_vs_l2_rank_comparison", "params": {"num_pairs": 10}}'
WHERE @cosine_story_code IS NOT NULL
AND NOT EXISTS (
    SELECT 1
    FROM surveys
    WHERE JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l2_rank_comparison'
);

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT
    @cosine_story_code,
    TRUE,
    '{"strategy": "cosine_similarity_vs_leontief_rank_comparison", "params": {"num_pairs": 10}}'
WHERE @cosine_story_code IS NOT NULL
AND NOT EXISTS (
    SELECT 1
    FROM surveys
    WHERE JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_leontief_rank_comparison'
);

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT
    @cosine_story_code,
    TRUE,
    '{"strategy": "cosine_similarity_vs_kl_rank_comparison", "params": {"num_pairs": 10}}'
WHERE @cosine_story_code IS NOT NULL
AND NOT EXISTS (
    SELECT 1
    FROM surveys
    WHERE JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_kl_rank_comparison'
);

COMMIT;
