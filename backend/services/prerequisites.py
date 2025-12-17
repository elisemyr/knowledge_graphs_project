from typing import Dict, List
from backend.database.neo4j import get_neo4j_client


def get_direct_prerequisites(course_code: str) -> List[str]:
    """get courses that are directly required"""
    client = get_neo4j_client()
    query = """
    MATCH (c:Course {code: $code})-[:PRE_REQUIRES]->(p:Course)
    RETURN p.code AS code
    ORDER BY code
    """
    results = client.query(query, {"code": course_code}, read_only=True)
    return [r["code"] for r in results]


def get_all_prerequisites(course_code: str) -> List[str]:
    """get ALL prerequisites = direct + indirect"""
    client = get_neo4j_client()
    query = """
    MATCH (c:Course {code: $code})-[:PRE_REQUIRES*1..10]->(p:Course)
    RETURN DISTINCT p.code AS code
    ORDER BY code
    """
    results = client.query(query, {"code": course_code}, read_only=True)
    return [r["code"] for r in results]


def detect_cycles(limit: int = 20) -> List[Dict]:
    """
    find cycles in the prerequisite graph (course A to course B and course B to course A)
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


def check_student_can_take(student_id: str, course_code: str) -> Dict:
    """
    check if a student can take a course
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

    results = client.query(query, {"student_id": student_id, "course_code": course_code}, read_only=True)

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


def validate_prerequisites_for_course(target_course: str, completed_courses: List[str]) -> Dict:
    """
    check if a list of completed courses satisfies all prerequisites for a target course
    """
    # prerequisites needed
    all_prereqs = get_all_prerequisites(target_course)

    # find what's missing
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
