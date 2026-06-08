from abc import ABC, abstractmethod
from typing import Tuple


class UtilityModel(ABC):
    """
    Abstract base class for all scoring utility models.
    Utility models must be stateless.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the utility model."""
        pass

    @property
    @abstractmethod
    def utility_type(self) -> str:
        """
        Category of the utility model (e.g., 'distance', 'ratio').
        """
        pass

    @abstractmethod
    def calculate(
        self, user_vec: Tuple[float, ...], candidate_vec: Tuple[float, ...]
    ) -> float:
        """
        Calculate the score for a candidate vector relative to a user's
        ideal vector.

        Higher Score = Better Match.
        (e.g., for distance models, this should return -distance).

        Args:
            user_vec: The user's ideal budget allocation.
            candidate_vec: A candidate budget allocation to score.

        Returns:
            A float score where higher is better.
        """
        pass
