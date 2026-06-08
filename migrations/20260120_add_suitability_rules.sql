-- Migration: Add suitability_rules to surveys table
-- Created: 2026-01-20

ALTER TABLE surveys ADD COLUMN suitability_rules JSON DEFAULT NULL AFTER awareness_pts;

-- Update existing surveys to maintain backward compatibility with zero-value constraints
UPDATE surveys 
SET suitability_rules = '{"max_zero_values": 0}' 
WHERE pair_generation_config->>'$.strategy' IN (
    'asymmetric_loss_distribution', 
    'component_symmetry_test', 
    'sign_symmetry_test', 
    'preference_ranking_survey', 
    'biennial_budget_preference', 
    'triangle_inequality_test', 
    'multi_dimensional_single_peaked_test'
);
