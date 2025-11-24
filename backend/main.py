from fastapi import FastAPI, HTTPException
from typing import List
from pydantic import BaseModel

from backend.database.neo4j import get_neo4j_client
from backend.services import prerequisites as prereq_service

app = FastAPI(title="Course Prerequisite Planner")


# health check

@app.get("/health")
def health_check() -> dict:
    client = get_neo4j_client()
    result = client.query("RETURN 1 AS ok")
    return {"status": "ok", "neo4j_ok": result[0]["ok"] == 1}



# prerequisite endpoints
@app.get("/courses/{course_code}/prerequisites")
def get_course_prereqs(course_code: str, all: bool = True):
    """
    Get prerequisites for a course.
    ?all=true -> transitive
    ?all=false -> direct only
    """
    if all:
        prereqs = prereq_service.get_all_prerequisites(course_code)
    else:
        prereqs = prereq_service.get_direct_prerequisites(course_code)

    return {
        "course": course_code,
        "prerequisites": prereqs,
        "mode": "all" if all else "direct",
    }


@app.get("/courses/cycles")
def get_cycles(limit: int = 20):
    """
    Return cycles in the PRE_REQUIRES graph (if any).
    """
    cycles = prereq_service.detect_cycles(limit=limit)
    return {"count": len(cycles), "cycles": cycles}



# is a student can take course?

@app.get("/students/{student_id}/can_take/{course_code}")
def can_student_take(student_id: str, course_code: str):
    """
    Check if a given student can take a course.
    """
    result = prereq_service.check_student_can_take(
        student_id=student_id, course_code=course_code
    )

    if result.get("reason") == "course_not_found":
        raise HTTPException(status_code=404, detail="Course not found")

    return result



# POST Validation

class ValidationRequest(BaseModel):
    target_course: str
    completed_courses: List[str]


@app.post("/validation/prerequisites")
def api_validate_prerequisites(payload: ValidationRequest):
    """
    Validate if a student (represented here by a list of completed courses)
    can take the target course.
    """
    result = prereq_service.validate_prerequisites_for_course(
        target_course=payload.target_course,
        completed_courses=payload.completed_courses,
    )
    return result
