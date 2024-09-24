# import pytest
# from utils.survey_utils import is_valid_vector, generate_awareness_check
# import os
# import sys

# # Add the parent directory to the system path to allow importing from the backend module.
# sys.path.append(
#     os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# )

# def test_is_valid_vector():
#     assert is_valid_vector([50, 30, 20]) == True
#     assert is_valid_vector([33, 33, 34]) == False
#     assert is_valid_vector([0, 0, 100]) == True
#     assert is_valid_vector([10, 20, 30, 40]) == True
#     assert is_valid_vector([]) == False
#     assert is_valid_vector([101]) == False
#     assert is_valid_vector([50, 50, 1]) == False

# def test_generate_awareness_check():
#     user_vector = [50, 30, 20]
#     result = generate_awareness_check(user_vector, 3)

#     assert isinstance(result, dict)
#     assert 'option1' in result
#     assert 'option2' in result
#     assert 'correct_answer' in result

#     assert result['option2'] == user_vector
#     assert result['correct_answer'] == 2
#     assert sum(result['option1']) == 100
#     assert result['option1'] != user_vector

# @pytest.mark.parametrize("num_subjects", [3, 4, 5])
# def test_generate_awareness_check_different_subjects(num_subjects):
#     user_vector = [20] * num_subjects
#     result = generate_awareness_check(user_vector, num_subjects)

#     assert len(result['option1']) == num_subjects
#     assert len(result['option2']) == num_subjects
#     assert sum(result['option1']) == 100
#     assert sum(result['option2']) == 100
