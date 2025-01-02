"""
Base classes for survey pair generation strategies.
Implements Strategy pattern for flexible pair generation algorithms.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Tuple, Type

import numpy as np

logger = logging.getLogger(__name__)


class PairGenerationStrategy(ABC):
    """Base class for implementing pair generation strategies."""

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
    ) -> List[Tuple[tuple, tuple]]:
        """
        Generate pairs based on strategy's logic.

        Args:
            user_vector: User's ideal budget allocation
            n: Number of pairs to generate
            vector_size: Size of each allocation vector

        Returns:
            List of tuple pairs representing budget allocations
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return unique identifier for this strategy."""
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
