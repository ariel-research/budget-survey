-- Add pair generation configuration column
ALTER TABLE surveys 
ADD COLUMN pair_generation_config JSON NULL;

-- Update existing rows with default configuration
UPDATE surveys 
SET pair_generation_config = '{"strategy": "optimization_metrics", "params": {"num_pairs": 10}}'
WHERE pair_generation_config IS NULL;

-- Make the column NOT NULL after setting defaults
ALTER TABLE surveys 
MODIFY COLUMN pair_generation_config JSON NOT NULL;