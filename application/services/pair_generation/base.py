"""
Base classes for survey pair generation strategies.
Implements Strategy pattern for flexible pair generation algorithms.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Tuple, Type, Union

import numpy as np

logger = logging.getLogger(__name__)


class PairGenerationStrategy(ABC):
    """Base class for implementing pair generation strategies."""

    def _format_vector_for_logging(self, vector: tuple) -> Tuple[tuple, int]:
        """
        Format vector for logging, converting values to integers.

        Args:
            vector: Vector to format

        Returns:
            Tuple containing formatted vector and its sum
        """
        formatted = tuple(int(v) for v in vector)
        return formatted, sum(formatted)

    def _log_pairs(self, pairs: List[Dict[str, tuple]]) -> None:
        """
        Log generated pairs with their sums.

        Args:
            pairs: List of dicts containing strategy descriptions and vectors
        """
        logger.info(f"Generated pairs using {self.__class__.__name__}:")
        for i, pair in enumerate(pairs, 1):
            # Extract vectors and descriptions
            descriptions = list(pair.keys())
            vectors = list(pair.values())

            vec_a_fmt, sum_a = self._format_vector_for_logging(vectors[0])
            vec_b_fmt, sum_b = self._format_vector_for_logging(vectors[1])

            logger.info(
                f"Pair {i}:\n"
                f"  {descriptions[0]}: {vec_a_fmt} (sum: {sum_a})\n"
                f"  {descriptions[1]}: {vec_b_fmt} (sum: {sum_b})"
            )

    def _validate_vector(self, vector: tuple, vector_size: int) -> None:
        """
        Validate vector properties.

        Args:
            vector: Vector to validate
            vector_size: Expected size of vector

        Raises:
            ValueError: If vector is invalid
        """
        if not vector or len(vector) != vector_size:
            raise ValueError(f"Vector must have length {vector_size}")
        if sum(vector) != 100:
            raise ValueError("Vector must sum to 100")
        if any(v < 0 or v > 100 for v in vector):
            raise ValueError("Vector values must be between 0 and 100")

    def get_table_columns(self) -> Dict[str, Dict]:
        """
        Get column definitions for the survey response breakdown table.

        Returns:
            Dict: Dictionary with column definitions where:
                - key: column identifier
                - value: dict with column properties (name, type, etc.)

        Default implementation returns columns based on option labels.
        Strategy implementations can override this to provide custom columns.
        """
        # Default implementation - uses option labels for column names
        option_labels = self.get_option_labels()
        return {
            "option1": {
                "name": option_labels[0],
                "type": "percentage",
                "highlight": True,
            },
            "option2": {
                "name": option_labels[1],
                "type": "percentage",
                "highlight": True,
            },
        }

    def create_random_vector(self, size: int = 3) -> tuple:
        """
        Generate a random vector of integers that sums to 100.

        Args:
            size: Number of elements in the vector

        Returns:
            tuple: Vector of integers summing to 100, each divisible by 5
        """
        vector = np.random.rand(size)
        vector = np.floor(vector / vector.sum() * 20).astype(int)
        vector[-1] = 20 - vector[:-1].sum()
        np.random.shuffle(vector)
        vector = vector * 5
        return tuple(vector)

    def generate_vector_pool(self, size: int, vector_size: int) -> Set[tuple]:
        """
        Generate a pool of unique random vectors.

        Args:
            size: Number of vectors to generate
            vector_size: Size of each vector

        Returns:
            Set of unique vectors
        """
        vector_pool = set()
        attempts = 0
        max_attempts = size * 20

        while len(vector_pool) < size and attempts < max_attempts:
            vector = self.create_random_vector(vector_size)
            vector_pool.add(vector)
            attempts += 1

        logger.debug(f"Generated vector pool of size {len(vector_pool)}")
        return vector_pool

    @abstractmethod
    def generate_pairs(
        self, user_vector: tuple, n: int, vector_size: int
    ) -> List[Dict[str, tuple]]:
        """
        Generate pairs based on strategy's logic.

        Args:
            user_vector: User's ideal budget allocation
            n: Number of pairs to generate
            vector_size: Size of each allocation vector

        Returns:
            List of dicts containing {'option_description': vector} pairs,
            where option_description includes strategy name and parameters
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return unique identifier for this strategy."""
        pass

    @abstractmethod
    def get_option_labels(self) -> Tuple[str, str]:
        """Return labels for the two options being compared."""
        pass

    def _are_absolute_canonical_identical(
        self, v1: Union[np.ndarray, list, tuple], v2: Union[np.ndarray, list, tuple]
    ) -> bool:
        """
        Check if vectors have identical absolute value canonical forms.

        This detects patterns that are equivalent in terms of absolute
        distances, preventing degenerate pairs that could compromise
        research validity.

        Args:
            v1: First vector to compare
            v2: Second vector to compare

        Returns:
            bool: True if vectors have same absolute canonical form

        Examples:
            Additive inverses are identical:
            >>> _are_absolute_canonical_identical([10, -5, -5], [-10, 5, 5])
            True  # Both become [5, 5, 10] when sorted by absolute value

            Different patterns are distinct:
            >>> _are_absolute_canonical_identical([20, -10, -10], [15, -10, -5])
            False  # [10, 10, 20] != [5, 10, 15]
        """
        v1_abs_canonical = tuple(sorted(abs(x) for x in v1))
        v2_abs_canonical = tuple(sorted(abs(x) for x in v2))
        return v1_abs_canonical == v2_abs_canonical

    def get_option_description(self, **kwargs) -> str:
        """
        Get descriptive name for an option including all metric values.

        Args:
            metric_type: Type of metric (e.g., 'sum', 'ratio', 'rss')
            best_value: The best value for this metric
            worst_value: The worst value for this metric

        Returns:
            str: Description with both metric values
        """
        metric_type = kwargs.get("metric_type")
        best_value = kwargs.get("best_value")
        worst_value = kwargs.get("worst_value")

        if any(val is None for val in [metric_type, best_value, worst_value]):
            import json

            logger.warning("Kwargs received: %s", json.dumps(kwargs, indent=2))
            return "Unknown Vector"

        return f"{self._get_metric_name(metric_type)}: {{best: {best_value:.2f}, worst: {worst_value:.2f}}}"

    @abstractmethod
    def _get_metric_name(self, metric_type: str) -> str:
        """Get the display name for a metric type."""
        pass


class StrategyRegistry:
    """
    Singleton registry for pair generation strategies.
    Manages strategy registration and retrieval.
    """

    _instance = None
    _strategies: Dict[str, Type[PairGenerationStrategy]] = {}

    def __new__(cls):
        if cls._instance is None:
            logger.debug("Creating new StrategyRegistry instance")
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            logger.debug("Initializing StrategyRegistry")

    @classmethod
    def register(cls, strategy_class: Type[PairGenerationStrategy]) -> None:
        """
        Register a new strategy.

        Args:
            strategy_class: Strategy class to register
        """
        strategy = strategy_class()
        strategy_name = strategy.get_strategy_name()
        cls._strategies[strategy_name] = strategy_class
        logger.info(f"Registered pair generation strategy: {strategy_name}")

    @classmethod
    def get_strategy(cls, strategy_name: str) -> PairGenerationStrategy:
        """
        Get strategy instance by name.

        Args:
            strategy_name: Name of the strategy to retrieve

        Returns:
            Instance of requested strategy

        Raises:
            ValueError: If strategy not found
        """
        if strategy_name not in cls._strategies:
            logger.error(f"Strategy not found: {strategy_name}")
            raise ValueError(f"Strategy '{strategy_name}' not found")

        logger.debug(f"Retrieved strategy: {strategy_name}")
        return cls._strategies[strategy_name]()
