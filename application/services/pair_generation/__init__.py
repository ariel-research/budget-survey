"""Package for survey pair generation strategies."""

from .asymmetric_loss_distribution import AsymmetricLossDistributionStrategy
from .base import PairGenerationStrategy, StrategyRegistry
from .cyclic_shift_strategy import CyclicShiftStrategy
from .dynamic_temporal_preference_strategy import DynamicTemporalPreferenceStrategy
from .extreme_vectors_strategy import ExtremeVectorsStrategy
from .linear_symmetry_strategy import LinearSymmetryStrategy
from .multi_dimensional_single_peaked import MultiDimensionalSinglePeakedStrategy
from .optimization_metrics_rank import OptimizationMetricsRankStrategy
from .optimization_metrics_vector import OptimizationMetricsStrategy
from .preference_ranking_survey import PreferenceRankingSurveyStrategy
from .rank_strategies import (
    L1VsL2RankStrategy,
    L1VsLeontiefRankStrategy,
    L2VsLeontiefRankStrategy,
)
from .root_sum_squared_ratio_vector import RootSumSquaredRatioStrategy
from .root_sum_squared_sum_vector import RootSumSquaredSumStrategy
from .rounded_weighted_average_vector import (
    RoundedWeightedAverageVectorStrategy,
)
from .triangle_inequality_strategy import TriangleInequalityStrategy
from .weighted_average_vector import WeightedAverageVectorStrategy

# Register strategies
StrategyRegistry.register(OptimizationMetricsStrategy)
StrategyRegistry.register(OptimizationMetricsRankStrategy)
StrategyRegistry.register(L1VsLeontiefRankStrategy)
StrategyRegistry.register(L1VsL2RankStrategy)
StrategyRegistry.register(L2VsLeontiefRankStrategy)
StrategyRegistry.register(WeightedAverageVectorStrategy)
StrategyRegistry.register(RoundedWeightedAverageVectorStrategy)
StrategyRegistry.register(PreferenceRankingSurveyStrategy)
StrategyRegistry.register(MultiDimensionalSinglePeakedStrategy)
StrategyRegistry.register(RootSumSquaredSumStrategy)
StrategyRegistry.register(RootSumSquaredRatioStrategy)
StrategyRegistry.register(ExtremeVectorsStrategy)
StrategyRegistry.register(CyclicShiftStrategy)
StrategyRegistry.register(LinearSymmetryStrategy)
StrategyRegistry.register(AsymmetricLossDistributionStrategy)
StrategyRegistry.register(DynamicTemporalPreferenceStrategy)
StrategyRegistry.register(TriangleInequalityStrategy)

__all__ = [
    "PairGenerationStrategy",
    "StrategyRegistry",
    "OptimizationMetricsStrategy",
    "OptimizationMetricsRankStrategy",
    "L1VsLeontiefRankStrategy",
    "L1VsL2RankStrategy",
    "L2VsLeontiefRankStrategy",
    "WeightedAverageVectorStrategy",
    "RoundedWeightedAverageVectorStrategy",
    "MultiDimensionalSinglePeakedStrategy",
    "RootSumSquaredSumStrategy",
    "RootSumSquaredRatioStrategy",
    "ExtremeVectorsStrategy",
    "CyclicShiftStrategy",
    "LinearSymmetryStrategy",
    "AsymmetricLossDistributionStrategy",
    "PreferenceRankingSurveyStrategy",
    "DynamicTemporalPreferenceStrategy",
    "TriangleInequalityStrategy",
]
