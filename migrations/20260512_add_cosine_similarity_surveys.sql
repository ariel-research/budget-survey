-- Migration: Add cosine similarity rank-comparison surveys for all stories
-- Date: 2026-05-12

START TRANSACTION;

-- ==========================================
-- 1. PRODUCTION STORIES
-- ==========================================

-- --- government_budget ---
INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'government_budget', TRUE, '{"strategy": "cosine_similarity_vs_l1_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'government_budget')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'government_budget' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l1_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'government_budget', TRUE, '{"strategy": "cosine_similarity_vs_l2_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'government_budget')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'government_budget' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l2_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'government_budget', TRUE, '{"strategy": "cosine_similarity_vs_leontief_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'government_budget')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'government_budget' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_leontief_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'government_budget', TRUE, '{"strategy": "cosine_similarity_vs_kl_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'government_budget')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'government_budget' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_kl_rank_comparison');


-- --- government_budget_4_subjects ---
INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'government_budget_4_subjects', TRUE, '{"strategy": "cosine_similarity_vs_l1_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'government_budget_4_subjects')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'government_budget_4_subjects' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l1_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'government_budget_4_subjects', TRUE, '{"strategy": "cosine_similarity_vs_l2_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'government_budget_4_subjects')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'government_budget_4_subjects' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l2_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'government_budget_4_subjects', TRUE, '{"strategy": "cosine_similarity_vs_leontief_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'government_budget_4_subjects')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'government_budget_4_subjects' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_leontief_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'government_budget_4_subjects', TRUE, '{"strategy": "cosine_similarity_vs_kl_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'government_budget_4_subjects')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'government_budget_4_subjects' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_kl_rank_comparison');


-- --- government_budget_5_subjects ---
INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'government_budget_5_subjects', TRUE, '{"strategy": "cosine_similarity_vs_l1_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'government_budget_5_subjects')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'government_budget_5_subjects' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l1_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'government_budget_5_subjects', TRUE, '{"strategy": "cosine_similarity_vs_l2_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'government_budget_5_subjects')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'government_budget_5_subjects' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l2_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'government_budget_5_subjects', TRUE, '{"strategy": "cosine_similarity_vs_leontief_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'government_budget_5_subjects')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'government_budget_5_subjects' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_leontief_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'government_budget_5_subjects', TRUE, '{"strategy": "cosine_similarity_vs_kl_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'government_budget_5_subjects')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'government_budget_5_subjects' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_kl_rank_comparison');


-- --- municipal_budget ---
INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'municipal_budget', TRUE, '{"strategy": "cosine_similarity_vs_l1_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'municipal_budget')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'municipal_budget' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l1_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'municipal_budget', TRUE, '{"strategy": "cosine_similarity_vs_l2_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'municipal_budget')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'municipal_budget' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l2_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'municipal_budget', TRUE, '{"strategy": "cosine_similarity_vs_leontief_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'municipal_budget')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'municipal_budget' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_leontief_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'municipal_budget', TRUE, '{"strategy": "cosine_similarity_vs_kl_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'municipal_budget')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'municipal_budget' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_kl_rank_comparison');


-- ==========================================
-- 2. DEVELOPMENT STORIES
-- ==========================================

-- --- budget_2024 ---
INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2024', TRUE, '{"strategy": "cosine_similarity_vs_l1_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2024')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2024' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l1_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2024', TRUE, '{"strategy": "cosine_similarity_vs_l2_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2024')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2024' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l2_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2024', TRUE, '{"strategy": "cosine_similarity_vs_leontief_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2024')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2024' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_leontief_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2024', TRUE, '{"strategy": "cosine_similarity_vs_kl_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2024')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2024' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_kl_rank_comparison');


-- --- budget_2025 ---
INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2025', TRUE, '{"strategy": "cosine_similarity_vs_l1_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2025')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2025' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l1_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2025', TRUE, '{"strategy": "cosine_similarity_vs_l2_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2025')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2025' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l2_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2025', TRUE, '{"strategy": "cosine_similarity_vs_leontief_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2025')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2025' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_leontief_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2025', TRUE, '{"strategy": "cosine_similarity_vs_kl_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2025')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2025' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_kl_rank_comparison');


-- --- budget_2026_4D ---
INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2026_4D', TRUE, '{"strategy": "cosine_similarity_vs_l1_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2026_4D')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2026_4D' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l1_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2026_4D', TRUE, '{"strategy": "cosine_similarity_vs_l2_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2026_4D')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2026_4D' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l2_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2026_4D', TRUE, '{"strategy": "cosine_similarity_vs_leontief_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2026_4D')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2026_4D' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_leontief_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2026_4D', TRUE, '{"strategy": "cosine_similarity_vs_kl_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2026_4D')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2026_4D' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_kl_rank_comparison');


-- --- budget_2027_5D ---
INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2027_5D', TRUE, '{"strategy": "cosine_similarity_vs_l1_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2027_5D')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2027_5D' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l1_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2027_5D', TRUE, '{"strategy": "cosine_similarity_vs_l2_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2027_5D')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2027_5D' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_l2_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2027_5D', TRUE, '{"strategy": "cosine_similarity_vs_leontief_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2027_5D')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2027_5D' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_leontief_rank_comparison');

INSERT INTO surveys (story_code, active, pair_generation_config)
SELECT 'budget_2027_5D', TRUE, '{"strategy": "cosine_similarity_vs_kl_rank_comparison", "params": {"num_pairs": 10}}'
WHERE EXISTS (SELECT 1 FROM stories WHERE code = 'budget_2027_5D')
AND NOT EXISTS (SELECT 1 FROM surveys WHERE story_code = 'budget_2027_5D' AND JSON_UNQUOTE(JSON_EXTRACT(pair_generation_config, '$.strategy')) = 'cosine_similarity_vs_kl_rank_comparison');

COMMIT;
