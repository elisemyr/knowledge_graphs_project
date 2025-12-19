"""
Eligibility API Routes

Endpoints for checking student eligibility for courses based on completed prerequisites.
"""

from fastapi import APIRouter, Query

from backend.models.eligibility import EligibilityResponse
from backend.services import prerequisites as prereq_service
from backend.services.eligibility_service import EligibilityService

router = APIRouter(
    prefix="/api/students",
    tags=["eligibility"],
)

# Create one shared instance of the service
eligibility_service = EligibilityService()


@router.get("/{student_id}/eligibility", response_model=EligibilityResponse)
def check_eligibility(
    student_id: str,
    course_id: str = Query(..., description="Course to check eligibility for")
) -> EligibilityResponse:
    """
    Check if a student is eligible to take a course.

    Args:
        student_id: The student ID to check eligibility for.
        course_id: The course code to check eligibility for.

    Returns:
        EligibilityResponse containing eligibility status and missing prerequisites.
    """
    # Get completed courses from the instance
    completed_courses = eligibility_service.get_completed_courses(student_id)

    # Get prerequisites using prerequisite service
    course_prereqs = prereq_service.get_all_prerequisites(course_id)

    # Compute missing prerequisites
    missing = eligibility_service.compute_missing_prerequisites(course_prereqs, completed_courses)

    # Build the response
    return eligibility_service.create_eligibility_response(student_id, course_id, missing)
