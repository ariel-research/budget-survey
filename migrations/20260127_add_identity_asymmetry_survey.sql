-- Migration: Add Survey - Identity Asymmetry
-- Date: 2026-01-27

START TRANSACTION;

INSERT IGNORE INTO surveys (story_code, active, suitability_rules, pair_generation_config)
VALUES (
    'government_budget', 
    TRUE,
    '{"min_equal_value_pair": 10}', 
    '{"strategy": "identity_asymmetry", "params": {"num_pairs": 10}}'
);

COMMIT;
