from fastapi import APIRouter
from backend.services.degree_planner_service import plan_degree

router = APIRouter(prefix="/api/students")


@router.get("/{student_id}/plan/sequence")
def degree_planner(student_id: str, target: str):
    return plan_degree(student_id, target)
