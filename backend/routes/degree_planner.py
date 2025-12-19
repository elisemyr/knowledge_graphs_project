"""
Degree Planner API Routes

Endpoints for generating degree completion plans and course sequences.
"""

from typing import Dict

from fastapi import APIRouter

from backend.services.degree_planner_service import plan_degree

router = APIRouter(prefix="/api/students")


@router.get("/{student_id}/plan/sequence")
def degree_planner(student_id: str, target: str) -> Dict:
    """
    Generate a degree completion plan for a student.

    Args:
        student_id: The student ID to plan for.
        target: The degree ID to plan completion for.

    Returns:
        Dictionary containing remaining courses and recommended sequence.
    """
    return plan_degree(student_id, target)
