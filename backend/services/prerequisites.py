# backend/services/prerequisites.py

from __future__ import annotations

from typing import Dict, List

from backend.database.neo4j import get_neo4j_client


def get_direct_prerequisites(course_code: str) -> List[str]:
    """
    Return the direct prerequisites of a course (1 hop PRE_REQUIRES).
    """
    client = get_neo4j_client()
    cypher = """
    MATCH (c:Course {code: $code})-[:PRE_REQUIRES]->(p:Course)
    RETURN p.code AS code
    ORDER BY code
    """
    records = client.query(cypher, {"code": course_code}, read_only=True)
    return [r["code"] for r in records]


def get_all_prerequisites(course_code: str) -> List[str]:
    """
    Return all (transitive) prerequisites of a course (multiple hops).
    """
    client = get_neo4j_client()
    cypher = """
    MATCH (c:Course {code: $code})-[:PRE_REQUIRES*1..10]->(p:Course)
    RETURN DISTINCT p.code AS code
    ORDER BY code
    """
    records = client.query(cypher, {"code": course_code}, read_only=True)
    return [r["code"] for r in records]


def detect_cycles(limit: int = 20) -> List[Dict]:
    """
    Detect cycles in the PRE_REQUIRES graph.

    Returns a list of dictionaries like:
    {
        "course": "CS 225",
        "length": 3,
        "path": ["CS 225", "CS 357", "CS 225"]
    }
    """
    client = get_neo4j_client()
    cypher = """
    MATCH p = (c:Course)-[:PRE_REQUIRES*1..10]->(c)
    RETURN c.code AS course,
           length(p) AS length,
           [n IN nodes(p) | n.code] AS path
    LIMIT $limit
    """
    records = client.query(cypher, {"limit": limit}, read_only=True)
    return records


def check_student_can_take(student_id: str, course_code: str) -> Dict:
    """
    Check whether a student can take a course, based on HAS_COMPLETED.

    Returns:
        {
          "student_id": "...",
          "course": "...",
          "required": [...],
          "completed": [...],
          "missing": [...],
          "can_take": True/False
        }
    """
    client = get_neo4j_client()

    cypher = """
    // Collect all required prerequisites for this course
    MATCH (target:Course {code: $course_code})
    OPTIONAL MATCH (target)-[:PRE_REQUIRES*1..10]->(req:Course)
    WITH target, COLLECT(DISTINCT req.code) AS required

    // Collect courses the student has completed
    OPTIONAL MATCH (s:Student {student_id: $student_id})
    OPTIONAL MATCH (s)-[:HAS_COMPLETED]->(done:Course)
    WITH target, required, s, COLLECT(DISTINCT done.code) AS completed

    RETURN
      target.code AS course,
      required,
      completed,
      s IS NOT NULL AS student_exists
    """

    records = client.query(
        cypher,
        {"student_id": student_id, "course_code": course_code},
        read_only=True,
    )

    if not records:
        # Course not found
        return {
            "student_id": student_id,
            "course": course_code,
            "required": [],
            "completed": [],
            "missing": [],
            "can_take": False,
            "reason": "course_not_found",
        }

    row = records[0]
    required = row.get("required") or []
    completed = row.get("completed") or []

    # If student doesn't exist, we can flag it
    if not row.get("student_exists", False):
        return {
            "student_id": student_id,
            "course": course_code,
            "required": required,
            "completed": completed,
            "missing": required,  # everything missing
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
