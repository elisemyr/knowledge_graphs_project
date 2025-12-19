"""
Prerequisites Service

Provides functions for querying course prerequisites, detecting cycles,
and validating student eligibility based on completed courses.
"""

from typing import Dict, List, Union

from backend.database.neo4j import get_neo4j_client


def get_direct_prerequisites(course_code: str) -> List[str]:
    """
    Get courses that are directly required as prerequisites.

    Args:
        course_code: The course code to get direct prerequisites for.

    Returns:
        List of course codes that are direct prerequisites, sorted alphabetically.
    """
    client = get_neo4j_client()
    query = """
    MATCH (c:Course {code: $code})-[:PRE_REQUIRES]->(p:Course)
    RETURN p.code AS code
    ORDER BY code
    """
    results = client.query(query, {"code": course_code}, read_only=True)
    return [r["code"] for r in results]


def get_all_prerequisites(course_code: str) -> List[str]:
    """
    Get all prerequisites (direct + indirect/transitive).

    Args:
        course_code: The course code to get all prerequisites for.

    Returns:
        List of all prerequisite course codes (direct and indirect), sorted alphabetically.
    """
    client = get_neo4j_client()
    query = """
    MATCH (c:Course {code: $code})-[:PRE_REQUIRES*1..10]->(p:Course)
    RETURN DISTINCT p.code AS code
    ORDER BY code
    """
    results = client.query(query, {"code": course_code}, read_only=True)
    return [r["code"] for r in results]


def detect_cycles(limit: int = 20) -> List[Dict[str, Union[str, int, List[str]]]]:
    """
    Find cycles in the prerequisite graph.

    A cycle occurs when course A requires course B, and course B (directly or indirectly)
    requires course A, creating a circular dependency.

    Args:
        limit: Maximum number of cycles to return.

    Returns:
        List of dictionaries, each containing course code, cycle length, and path of courses.
    """
    client = get_neo4j_client()
    query = """
    MATCH p = (c:Course)-[:PRE_REQUIRES*1..10]->(c)
    RETURN c.code AS course,
           length(p) AS length,
           [n IN nodes(p) | n.code] AS path
    LIMIT $limit
    """
    results = client.query(query, {"limit": limit}, read_only=True)
    return results


def check_student_can_take(
    student_id: str, course_code: str
) -> Dict[str, Union[str, List[str], bool]]:
    """
    Check if a student can take a course based on completed prerequisites.

    Args:
        student_id: The student ID to check.
        course_code: The course code to check eligibility for.

    Returns:
        Dictionary containing:
        - student_id: Student ID
        - course: Course code
        - required: List of required prerequisite course codes
        - completed: List of completed course codes
        - missing: List of missing prerequisite course codes
        - can_take: Boolean indicating if student can take the course
        - reason: Reason code ("ok", "course_not_found",
          "student_not_found", "missing_prerequisites")
    """
    client = get_neo4j_client()

    # get all prerequisites for the course
    query = """
    MATCH (target:Course {code: $course_code})
    OPTIONAL MATCH (target)-[:PRE_REQUIRES*1..10]->(req:Course)
    WITH target, COLLECT(DISTINCT req.code) AS required
    
    OPTIONAL MATCH (s:Student {student_id: $student_id})
    OPTIONAL MATCH (s)-[:HAS_COMPLETED]->(done:Course)
    WITH target, required, s, COLLECT(DISTINCT done.code) AS completed
    
    RETURN target.code AS course, required, completed, s IS NOT NULL AS student_exists
    """

    results = client.query(
        query, {"student_id": student_id, "course_code": course_code}, read_only=True
    )

    if not results:
        return {
            "student_id": student_id,
            "course": course_code,
            "required": [],
            "completed": [],
            "missing": [],
            "can_take": False,
            "reason": "course_not_found",
        }

    row = results[0]
    required = row.get("required") or []
    completed = row.get("completed") or []

    if not row.get("student_exists", False):
        return {
            "student_id": student_id,
            "course": course_code,
            "required": required,
            "completed": completed,
            "missing": required,
            "can_take": False,
            "reason": "student_not_found",
        }

    missing = sorted(list(set(required) - set(completed)))

    return {
        "student_id": student_id,
        "course": row["course"],
        "required": required,
        "completed": completed,
        "missing": missing,
        "can_take": len(missing) == 0,
        "reason": "ok" if len(missing) == 0 else "missing_prerequisites",
    }


def validate_prerequisites_for_course(
    target_course: str, completed_courses: List[str]
) -> Dict[str, Union[str, bool, List[str]]]:
    """
    Check if a list of completed courses satisfies all prerequisites for a target course.

    Args:
        target_course: The course code to validate prerequisites for.
        completed_courses: List of course codes the student has completed.

    Returns:
        Dictionary containing:
        - course: Target course code
        - can_take: Boolean indicating if prerequisites are satisfied
        - required_prerequisites: List of all required prerequisite course codes
        - missing_prerequisites: List of missing prerequisite course codes
        - completed_courses: List of completed course codes (sorted)
    """
    all_prereqs = get_all_prerequisites(target_course)

    required_set = set(all_prereqs)
    completed_set = set(completed_courses)
    missing = sorted(list(required_set - completed_set))

    return {
        "course": target_course,
        "can_take": len(missing) == 0,
        "required_prerequisites": sorted(all_prereqs),
        "missing_prerequisites": missing,
        "completed_courses": sorted(completed_set),
    }
