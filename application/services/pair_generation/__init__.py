"""Package for survey pair generation strategies."""

from .base import PairGenerationStrategy, StrategyRegistry
from .optimization_metrics_vector import OptimizationMetricsStrategy
from .rounded_weighted_average_vector import RoundedWeightedAverageVectorStrategy
from .weighted_average_vector import WeightedAverageVectorStrategy

# Register strategies
StrategyRegistry.register(OptimizationMetricsStrategy)
StrategyRegistry.register(WeightedAverageVectorStrategy)
StrategyRegistry.register(RoundedWeightedAverageVectorStrategy)

__all__ = [
    "PairGenerationStrategy",
    "StrategyRegistry",
    "OptimizationMetricsStrategy",
    "WeightedAverageVectorStrategy",
    "RoundedWeightedAverageVectorStrategy",
]
