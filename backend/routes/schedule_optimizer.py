"""
Schedule Optimization API Routes
"""

from fastapi import APIRouter, HTTPException, Query
from backend.models.schedule import OptimizedScheduleResponse, ScheduleConstraints
from backend.services.schedule_optimizer_service import get_schedule_optimizer_service

router = APIRouter(prefix="/api/students", tags=["Schedule Optimization"])


@router.get(
    "/{student_id}/schedule/optimize",
    response_model=OptimizedScheduleResponse,
    summary="Get optimized course schedule for a student",
    description="""
    Generate an optimized course schedule for a student that:
    - Respects prerequisite dependencies
    - Balances course load across semesters
    - Only schedules courses when they're offered
    - Considers courses already completed
    
    The schedule uses topological sorting to ensure prerequisites are taken first,
    and distributes courses across semesters to avoid overload.
    """,
)
async def optimize_schedule(
    student_id: str,
    max_courses_per_semester: int = Query(5, ge=1, le=8, description="Maximum number of courses per semester"),
    max_credits_per_semester: int = Query(18, ge=6, le=24, description="Maximum credit hours per semester"),
    target_semesters: int = Query(8, ge=1, le=12, description="Number of semesters to plan for"),
    start_semester: str = Query("FALL_2024", description="Starting semester ID (e.g., 'FALL_2024')"),
) -> OptimizedScheduleResponse:
    """
    Optimize course schedule for a student

    Example:
        GET /api/students/S001/schedule/optimize?max_courses_per_semester=5&target_semesters=8
    """
    try:
        # Build constraints
        constraints = ScheduleConstraints(
            max_courses_per_semester=max_courses_per_semester,
            max_credits_per_semester=max_credits_per_semester,
            target_semesters=target_semesters,
            start_semester=start_semester,
        )

        # Get service and optimize schedule
        service = get_schedule_optimizer_service()
        result = service.optimize_schedule(student_id, constraints)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing schedule: {str(e)}")


@router.get(
    "/{student_id}/schedule/semesters",
    summary="Get available semesters for scheduling",
    description="Get list of available semesters with course offerings",
)
async def get_available_semesters(
    student_id: str,
    start_semester: str = Query("FALL_2024", description="Starting semester"),
    limit: int = Query(8, ge=1, le=20, description="Number of semesters to return"),
):
    """
    Get available semesters for a student

    Example:
        GET /api/students/S001/schedule/semesters?limit=8
    """
    try:
        from backend.database.neo4j import get_neo4j_driver

        driver = get_neo4j_driver()

        with driver.session() as session:
            query = """
            MATCH (s:Semester)
            WHERE s.id >= $start_semester
            OPTIONAL MATCH (c:Course)-[:OFFERED_IN]->(s)
            WITH s, count(c) as course_count
            RETURN s.id as id,
                   s.name as name,
                   s.year as year,
                   s.term as term,
                   course_count
            ORDER BY s.order
            LIMIT $limit
            """
            result = session.run(query, start_semester=start_semester, limit=limit)

            semesters = []
            for record in result:
                semesters.append(
                    {
                        "id": record["id"],
                        "name": record["name"],
                        "year": record["year"],
                        "term": record["term"],
                        "courses_offered": record["course_count"],
                    }
                )

            return {"student_id": student_id, "semesters": semesters, "total": len(semesters)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching semesters: {str(e)}")
