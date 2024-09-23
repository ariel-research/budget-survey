import random
from typing import Any, Dict, List


def is_valid_vector(vector: List[int]) -> bool:
    return sum(vector) == 100 and all(v % 5 == 0 for v in vector)


def generate_awareness_check(user_vector: List[int]) -> Dict[str, Any]:
    """Generate an awareness check question."""
    while True:
        fake_vector = [random.choice(range(0, 101, 5)) for _ in range(3)]
        if sum(fake_vector) == 100 and fake_vector != user_vector:
            break

    return {"option1": fake_vector, "option2": user_vector, "correct_answer": 2}
