"""Package for survey pair generation strategies."""

from .base import PairGenerationStrategy, StrategyRegistry
from .optimization import OptimizationMetricsStrategy
from .weighted_vector import WeightedVectorStrategy

# Register strategies
StrategyRegistry.register(OptimizationMetricsStrategy)
StrategyRegistry.register(WeightedVectorStrategy)

__all__ = [
    "PairGenerationStrategy",
    "StrategyRegistry",
    "OptimizationMetricsStrategy",
    "WeightedVectorStrategy",
]
