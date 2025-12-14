"""
Advanced Queries API Routes
Exposes complex Cypher query patterns via REST API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from backend.services.advanced_queries_service import get_advanced_queries_service

router = APIRouter(prefix="/api/advanced", tags=["Advanced Queries"])


@router.get(
    "/courses/{course_code}/prerequisite-chain",
    summary="Get deep prerequisite chain (depth >= 3)",
    description="""
    Find prerequisite chains of depth 3 or more for a course.
    
    This demonstrates:
    - Variable-length path traversal [:PRE_REQUIRES*3..]
    - WITH clauses for data transformation
    - Complex filtering and aggregation
    """
)
async def get_prerequisite_chain(
    course_code: str,
    min_depth: int = Query(3, ge=1, le=10, description="Minimum chain depth")
):
    """
    Example: GET /api/advanced/courses/CS%20374/prerequisite-chain?min_depth=3
    """
    try:
        service = get_advanced_queries_service()
        result = service.get_deep_prerequisite_chain(course_code, min_depth)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing prerequisite chain: {str(e)}"
        )


@router.get(
    "/students/{student_id}/next-courses",
    summary="Get next available courses with detailed analysis",
    description="""
    Find courses a student can take with prerequisite analysis.
    
    This demonstrates:
    - Multiple OPTIONAL MATCH clauses
    - UNWIND for list processing
    - Complex WHERE predicates with all()
    - Readiness scoring algorithm
    """
)
async def get_next_courses_analysis(
    student_id: str,
    semester_id: str = Query("FALL_2024", description="Target semester ID")
):
    """
    Example: GET /api/advanced/students/S001/next-courses?semester_id=FALL_2024
    """
    try:
        service = get_advanced_queries_service()
        courses = service.get_next_courses_with_analysis(student_id, semester_id)
        
        return {
            "student_id": student_id,
            "semester_id": semester_id,
            "courses": courses,
            "total_found": len(courses)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing next courses: {str(e)}"
        )


@router.get(
    "/courses/difficulty-analysis",
    summary="Analyze course difficulty and impact",
    description="""
    Analyze courses based on prerequisite complexity and downstream impact.
    
    This demonstrates:
    - Multiple recursive traversals
    - Path analysis with max() depth
    - Complex scoring algorithms
    - Course categorization logic
    """
)
async def analyze_course_difficulty(
    department: Optional[str] = Query(
        None,
        description="Filter by department prefix (e.g., 'CS', 'MATH')"
    ),
    limit: int = Query(50, ge=1, le=500, description="Maximum courses to return")
):
    """
    Example: GET /api/advanced/courses/difficulty-analysis?department=CS&limit=20
    """
    try:
        service = get_advanced_queries_service()
        courses = service.analyze_course_difficulty_and_impact(department)
        
        # Apply limit
        courses = courses[:limit]
        
        return {
            "department": department or "All",
            "courses": courses,
            "total_analyzed": len(courses)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing course difficulty: {str(e)}"
        )


@router.post(
    "/students/compare",
    summary="Compare progress of multiple students",
    description="""
    Compare academic progress of multiple students.
    
    This demonstrates:
    - UNWIND for batch processing
    - Multiple WITH clauses
    - Complex aggregations
    - Comparative analytics
    """
)
async def compare_students(
    student_ids: List[str]
):
    """
    Example POST body:
    {
        "student_ids": ["S001", "S002", "S003"]
    }
    
    Or use query params:
    POST /api/advanced/students/compare?student_ids=S001&student_ids=S002
    """
    try:
        if not student_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one student_id required"
            )
        
        if len(student_ids) > 20:
            raise HTTPException(
                status_code=400,
                detail="Maximum 20 students can be compared at once"
            )
        
        service = get_advanced_queries_service()
        result = service.compare_student_progress(student_ids)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error comparing students: {str(e)}"
        )


# Allow query params version of compare
@router.get(
    "/students/compare",
    summary="Compare students (GET version)",
    description="Same as POST but using query parameters"
)
async def compare_students_get(
    student_ids: List[str] = Query(..., description="Student IDs to compare")
):
    """
    Example: GET /api/advanced/students/compare?student_ids=S001&student_ids=S002
    """
    return await compare_students(student_ids)