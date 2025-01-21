from datetime import datetime, timezone
from typing import Any, Dict, List


class ResponseFormatter:
    """Formats survey responses consistently."""

    @staticmethod
    def get_current_utc_time() -> str:
        """
        Get current UTC time in ISO format.

        Returns:
            str: Current UTC time in ISO format with timezone information
        """
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def format_response_data(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format response data with consistent structure and metadata.

        Args:
            responses: List of response dictionaries

        Returns:
            Dict[str, Any]: Formatted response data with metadata
        """
        if not responses:
            return {
                "total_responses": 0,
                "responses": [],
                "metadata": {
                    "generated_at": ResponseFormatter.get_current_utc_time(),
                    "version": "1.0",
                },
            }

        return {
            "survey_id": responses[0].get("survey_id"),
            "total_responses": len(responses),
            "responses": responses,
            "metadata": {
                "generated_at": ResponseFormatter.get_current_utc_time(),
                "version": "1.0",
            },
        }
