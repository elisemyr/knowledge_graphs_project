"""
Eligibility Models

Pydantic models for student course eligibility responses.
"""

from typing import List

from pydantic import BaseModel


class EligibilityResponse(BaseModel):
    """Response model for student course eligibility check."""

    student_id: str
    course_id: str
    eligible: bool
    missing_prerequisites: List[str]
