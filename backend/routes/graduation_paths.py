from fastapi import APIRouter, HTTPException
from backend.services.graduation_paths_service import generate_graduation_paths

router = APIRouter(prefix="/api/students", tags=["Graduation Paths"])


@router.get("/{student_id}/paths/graduation")
async def get_graduation_paths(student_id: str):
    try:
        return generate_graduation_paths(student_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
