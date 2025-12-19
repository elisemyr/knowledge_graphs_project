"""
Course Prerequisite Planner API

Main FastAPI application for managing course prerequisites, student eligibility,
degree planning, and schedule optimization using Neo4j graph database.
"""

from typing import Dict, List, Union

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.database.neo4j import get_neo4j_client
from backend.services import prerequisites as prereq_service
from backend.routes import eligibility
from backend.routes.degree_planner import router as degree_planner_router
from backend.routes.graduation_paths import router as paths_router
from backend.routes import schedule_optimizer

app = FastAPI(title="Course Prerequisite Planner")


@app.get("/")
def root() -> Dict[str, str]:
    """
    Root endpoint providing API information.

    Returns:
        Dictionary containing API metadata including message, version, docs, and health endpoints.
    """
    return {
        "message": "Course Prerequisite Planner API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health_check() -> Dict[str, bool]:
    """
    Health check endpoint to verify API and Neo4j connectivity.

    Returns:
        Dictionary with status and Neo4j connection status.
    """
    client = get_neo4j_client()
    result = client.query("RETURN 1 AS ok")
    return {"status": "ok", "neo4j_ok": result[0]["ok"] == 1}


@app.get("/courses/{course_code}/prerequisites")
def get_course_prereqs(course_code: str, all: bool = True) -> Dict[str, Union[str, List[str]]]:
    """
    Get prerequisites for a course.

    Args:
        course_code: The course code to get prerequisites for.
        all: If True, returns all prerequisites (transitive). If False, returns only direct prerequisites.

    Returns:
        Dictionary containing course code, prerequisites list, and mode (all/direct).
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
def get_cycles(limit: int = 20) -> Dict[str, Union[int, List[Dict]]]:
    """
    Return cycles in the PRE_REQUIRES graph (if any).

    Args:
        limit: Maximum number of cycles to return.

    Returns:
        Dictionary containing count and list of cycles found.
    """
    cycles = prereq_service.detect_cycles(limit=limit)
    return {"count": len(cycles), "cycles": cycles}


@app.get("/students/{student_id}/can_take/{course_code}")
def can_student_take(student_id: str, course_code: str) -> Dict:
    """
    Check if a given student can take a course.

    Args:
        student_id: The student ID to check.
        course_code: The course code to check eligibility for.

    Returns:
        Dictionary containing eligibility information including required, completed,
        missing prerequisites, and whether the student can take the course.

    Raises:
        HTTPException: 404 if course not found.
    """
    result = prereq_service.check_student_can_take(
        student_id=student_id, course_code=course_code
    )

    if result.get("reason") == "course_not_found":
        raise HTTPException(status_code=404, detail="Course not found")

    return result


class ValidationRequest(BaseModel):
    """Request model for prerequisite validation."""

    target_course: str
    completed_courses: List[str]


@app.post("/validation/prerequisites")
def api_validate_prerequisites(payload: ValidationRequest) -> Dict:
    """
    Validate if a student (represented by a list of completed courses) can take the target course.

    Args:
        payload: ValidationRequest containing target course and completed courses list.

    Returns:
        Dictionary containing validation result with required and missing prerequisites.
    """
    result = prereq_service.validate_prerequisites_for_course(
        target_course=payload.target_course,
        completed_courses=payload.completed_courses,
    )
    return result


app.include_router(eligibility.router)
app.include_router(degree_planner_router)
app.include_router(paths_router)
app.include_router(schedule_optimizer.router)

