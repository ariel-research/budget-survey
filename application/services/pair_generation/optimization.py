"""Implementation of the optimization metrics pair generation strategy."""

import logging
from typing import List, Tuple

from application.services.pair_generation.base import PairGenerationStrategy
from application.services.survey_vector_generator import (
    generate_optimization_metric_pairs,
)

logger = logging.getLogger(__name__)


class OptimizationMetricsStrategy(PairGenerationStrategy):
    """Strategy using optimization metrics for pair generation."""

    def generate_pairs(
        self, user_vector: tuple, n: int, vector_size: int
    ) -> List[Tuple[tuple, tuple]]:
        """
        Generate pairs using optimization metrics approach.

        Args:
            user_vector: User's ideal budget allocation
            n: Number of pairs to generate
            vector_size: Size of each allocation vector

        Returns:
            List of tuple pairs representing budget allocations
        """
        logger.debug(f"Generating {n} pairs using optimization metrics strategy")
        return generate_optimization_metric_pairs(user_vector, n, vector_size)

    def get_strategy_name(self) -> str:
        """Get the unique identifier for this strategy."""
        return "optimization_metrics"
