from pydantic import BaseModel
from typing import List


class EligibilityResponse(BaseModel):
    student_id: str
    course_id: str
    eligible: bool
    missing_prerequisites: List[str]
