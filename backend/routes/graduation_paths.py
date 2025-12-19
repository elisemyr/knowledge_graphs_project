"""
Graduation Paths API Routes

Endpoints for generating all possible graduation paths for students.
"""

from typing import Dict

from fastapi import APIRouter, HTTPException

from backend.services.graduation_paths_service import generate_graduation_paths

router = APIRouter(prefix="/api/students", tags=["Graduation Paths"])


@router.get("/{student_id}/paths/graduation")
async def get_graduation_paths(student_id: str) -> Dict:
    """
    Get all possible graduation paths for a student.

    Args:
        student_id: The student ID to generate paths for.

    Returns:
        Dictionary containing all valid course orderings for graduation.

    Raises:
        HTTPException: 500 if an error occurs during path generation.
    """
    try:
        return generate_graduation_paths(student_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
