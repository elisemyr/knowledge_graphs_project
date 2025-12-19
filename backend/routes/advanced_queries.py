"""
Advanced Queries API Routes
Exposes complex Cypher query patterns via REST API
"""

from fastapi import APIRouter, HTTPException, Query
from backend.services.advanced_queries_service import get_advanced_queries_service

router = APIRouter(prefix="/api/advanced", tags=["Advanced Queries"])


@router.get(
    "/bottleneck-courses",
    summary="Find bottleneck courses",
    description="""
    Identify courses that are critical bottlenecks in the curriculum.
    
    Bottleneck courses are those that:
    - Unlock many other courses (high dependent count)
    - Require multiple prerequisites themselves
    
    **Use case:** Helps administrators identify where to add more sections
    or provide additional support to prevent student delays.
    
    **Advanced Cypher patterns:**
    - OPTIONAL MATCH with multiple patterns
    - Variable-length paths: [:PRE_REQUIRES*1..3]
    - Multiple WITH clauses for data transformation
    - Collection and aggregation functions
    """,
)
async def find_bottleneck_courses(
    min_dependents: int = Query(3, ge=1, le=20, description="Minimum number of courses this must unlock"),
    min_prerequisites: int = Query(2, ge=1, le=10, description="Minimum prerequisites required"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
):
    """
    Find courses that are bottlenecks in the curriculum.

    Example:
        GET /api/queries/bottleneck-courses?min_dependents=3&min_prerequisites=2&limit=10
    """
    try:
        service = get_advanced_queries_service()
        courses = service.find_bottleneck_courses(
            min_dependents=min_dependents, min_prerequisites=min_prerequisites, limit=limit
        )

        return {
            "bottleneck_courses": courses,
            "total_found": len(courses),
            "filters": {"min_dependents": min_dependents, "min_prerequisites": min_prerequisites},
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error finding bottleneck courses: {str(exc)}")


@router.get(
    "/students/{student_id}/recommendations",
    summary="Get personalized course recommendations",
    description="""
    Get personalized course recommendations for a student for a specific semester.
    
    Calculates a "readiness score" (0-100) based on:
    - Completed prerequisites
    - How many future courses this unlocks
    
    **Use case:** Academic advising - suggest courses the student can realistically take.
    
    **Advanced Cypher patterns:**
    - Multiple OPTIONAL MATCH patterns
    - List comprehension with WHERE filtering
    - Complex CASE expressions for scoring
    - Computed metrics and filtering
    """,
)
async def get_course_recommendations(
    student_id: str,
    semester_id: str = Query("FALL_2024", description="Target semester ID (e.g., 'FALL_2024', 'SPRING_2025')"),
    min_readiness: int = Query(75, ge=0, le=100, description="Minimum readiness score (0-100)"),
    limit: int = Query(15, ge=1, le=50, description="Maximum recommendations to return"),
):
    """
    Get personalized course recommendations with readiness scores.

    Example:
        GET /api/queries/students/S001/recommendations?semester_id=FALL_2024&min_readiness=75
    """
    try:
        service = get_advanced_queries_service()
        result = service.get_course_recommendations(
            student_id=student_id, semester_id=semester_id, min_readiness=min_readiness, limit=limit
        )

        return result

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error getting recommendations: {str(exc)}")


@router.get(
    "/students/{student_id}/course-depth",
    summary="Get courses organized by prerequisite depth",
    description="""
    Show remaining courses organized by how many prerequisite levels they require.
    
    Categorizes courses as:
    - **Ready Now**: All prerequisites complete
    - **Almost Ready**: Only 1 prerequisite missing
    - **Plan Soon**: 2 prerequisites missing
    - **Plan Later**: 3+ prerequisites missing
    
    **Use case:** Helps students visualize their path to graduation and prioritize courses.
    
    **Advanced Cypher patterns:**
    - List comprehension with filtering
    - Variable-length paths with bounds: [:PRE_REQUIRES*1..5]
    - max(length(path)) for depth calculation
    - Multiple WITH clauses
    - CASE expressions for categorization
    """,
)
async def get_courses_by_depth(
    student_id: str, limit: int = Query(20, ge=1, le=100, description="Maximum courses to return")
):
    """
    Get remaining courses organized by prerequisite depth.

    Example:
        GET /api/queries/students/S001/course-depth?limit=20
    """
    try:
        service = get_advanced_queries_service()
        result = service.get_courses_by_prerequisite_depth(student_id=student_id, limit=limit)

        return result

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error analyzing course depth: {str(exc)}")


@router.get(
    "/students/{student_id}/summary",
    summary="Get comprehensive student progress summary",
    description="""
    Combines all three queries to give a complete picture of student progress.
    
    Returns:
    - Course recommendations for next semester
    - Courses organized by readiness
    - Overall progress metrics
    """,
)
async def get_student_summary(student_id: str, semester_id: str = Query("FALL_2024", description="Target semester")):
    """
    Get comprehensive summary combining all analysis.

    Example:
        GET /api/queries/students/S001/summary?semester_id=FALL_2024
    """
    try:
        service = get_advanced_queries_service()

        # Get recommendations
        recommendations = service.get_course_recommendations(
            student_id=student_id, semester_id=semester_id, min_readiness=75, limit=10
        )

        # Get course depth analysis
        depth_analysis = service.get_courses_by_prerequisite_depth(student_id=student_id, limit=20)

        return {
            "student_id": student_id,
            "student_name": recommendations.get("student_name"),
            "program": recommendations.get("program"),
            "completed_courses": depth_analysis.get("completed_courses", 0),
            "next_semester": {
                "semester_id": semester_id,
                "recommendations": recommendations.get("recommendations", []),
                "total_recommended": recommendations.get("total_recommendations", 0),
            },
            "remaining_courses": {
                "by_status": depth_analysis.get("courses_by_status", {}),
                "total_remaining": depth_analysis.get("total_remaining", 0),
            },
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generating student summary: {str(exc)}")
