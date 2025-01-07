"""Package for survey pair generation strategies."""

from .base import PairGenerationStrategy, StrategyRegistry
from .optimization import OptimizationMetricsStrategy
from .weighted_average_vector import WeightedAverageVectorStrategy

# Register strategies
StrategyRegistry.register(OptimizationMetricsStrategy)
StrategyRegistry.register(WeightedAverageVectorStrategy)

__all__ = [
    "PairGenerationStrategy",
    "StrategyRegistry",
    "OptimizationMetricsStrategy",
    "WeightedAverageVectorStrategy",
]
