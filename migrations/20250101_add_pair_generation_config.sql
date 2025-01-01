-- Add pair generation configuration to surveys table
ALTER TABLE surveys
ADD COLUMN pair_generation_config JSON NOT NULL DEFAULT '{"strategy": "optimization_metrics", "params": {"num_pairs": 10}}';