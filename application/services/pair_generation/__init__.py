"""Package for survey pair generation strategies."""

from .base import PairGenerationStrategy, StrategyRegistry
from .optimization import OptimizationMetricsStrategy

# Register default strategy
StrategyRegistry.register(OptimizationMetricsStrategy)

__all__ = ["PairGenerationStrategy", "StrategyRegistry", "OptimizationMetricsStrategy"]
