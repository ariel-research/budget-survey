class SurveyError(Exception):
    """Base exception class for survey-related errors."""

    def __init__(self, message: str = "An error occurred with the survey"):
        self.message = message
        super().__init__(self.message)


class SurveyNotFoundError(SurveyError):
    """
    Raised when a survey is not found in the database.

    Example:
        raise SurveyNotFoundError(survey_id=123)
    """

    def __init__(self, survey_id: int):
        self.survey_id = survey_id
        message = f"Survey {survey_id} not found"
        super().__init__(message)


class ResponseProcessingError(SurveyError):
    """
    Raised when there's an error processing survey responses.

    Example:
        raise ResponseProcessingError("Failed to process survey response data")
    """

    def __init__(self, message: str = "Error processing survey responses"):
        super().__init__(message)


class StrategyConfigError(SurveyError):
    """
    Raised when there's an error with survey strategy configuration.

    Example:
        raise StrategyConfigError(survey_id=123, strategy="l1_vs_leontief_comparison")
    """

    def __init__(self, survey_id: int, strategy: str):
        self.survey_id = survey_id
        self.strategy = strategy
        message = f"Invalid strategy configuration '{strategy}' for survey {survey_id}"
        super().__init__(message)


class UnsuitableForStrategyError(SurveyError):
    """
    Raised when user's ideal vector is unsuitable for a strategy.

    Example:
        raise UnsuitableForStrategyError("User vector contains zero values")
    """

    def __init__(self, message: str = "User vector is unsuitable for this strategy"):
        super().__init__(message)
