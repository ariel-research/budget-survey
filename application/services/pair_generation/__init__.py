"""Package for survey pair generation strategies."""

from .base import PairGenerationStrategy, StrategyRegistry
from .cyclic_shift_strategy import CyclicShiftStrategy
from .extreme_vectors_strategy import ExtremeVectorsStrategy
from .optimization_metrics_vector import OptimizationMetricsStrategy
from .root_sum_squared_ratio_vector import RootSumSquaredRatioStrategy
from .root_sum_squared_sum_vector import RootSumSquaredSumStrategy
from .rounded_weighted_average_vector import (
    RoundedWeightedAverageVectorStrategy,
)
from .weighted_average_vector import WeightedAverageVectorStrategy

# Register strategies
StrategyRegistry.register(OptimizationMetricsStrategy)
StrategyRegistry.register(WeightedAverageVectorStrategy)
StrategyRegistry.register(RoundedWeightedAverageVectorStrategy)
StrategyRegistry.register(RootSumSquaredSumStrategy)
StrategyRegistry.register(RootSumSquaredRatioStrategy)
StrategyRegistry.register(ExtremeVectorsStrategy)
StrategyRegistry.register(CyclicShiftStrategy)

__all__ = [
    "PairGenerationStrategy",
    "StrategyRegistry",
    "OptimizationMetricsStrategy",
    "WeightedAverageVectorStrategy",
    "RoundedWeightedAverageVectorStrategy",
    "RootSumSquaredSumStrategy",
    "RootSumSquaredRatioStrategy",
    "ExtremeVectorsStrategy",
    "CyclicShiftStrategy",
]
