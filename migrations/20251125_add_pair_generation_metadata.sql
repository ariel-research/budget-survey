-- Migration: Add generation metadata to comparison_pairs
-- Date: 2025-11-25
-- Description: Add generation_metadata JSON column to comparison_pairs table
--              to store pair generation metadata (e.g., relaxation level, epsilon)
--              for strategies that use adaptive generation algorithms.

ALTER TABLE `comparison_pairs`
ADD COLUMN `generation_metadata` JSON DEFAULT NULL
COMMENT 'Metadata about pair generation (e.g., relaxation level, epsilon)';





