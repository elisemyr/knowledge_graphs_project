from fastapi import APIRouter, Query
from backend.models.eligibility import EligibilityResponse
from backend.services.eligibility_service import EligibilityService
from backend.services import prerequisites as prereq_service

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
):
    # 1. Get completed courses from the instance
    completed_courses = eligibility_service.get_completed_courses(student_id)

    # 2. Get prerequisites using Elise's service
    course_prereqs = prereq_service.get_all_prerequisites(course_id)

    # 3. Compute missing prerequisites
    missing = eligibility_service.compute_missing_prerequisites(
        course_prereqs,
        completed_courses
    )

    # 4. Build the response
    return eligibility_service.create_eligibility_response(
        student_id,
        course_id,
        missing
    )
