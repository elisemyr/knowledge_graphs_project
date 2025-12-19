"""
Degree Planner Service

Provides functions for planning degree completion by determining remaining courses
and generating a recommended sequence based on prerequisite dependencies.
"""

from typing import Dict, List, Optional, Union

from backend.database.neo4j import get_neo4j_client


def get_degree_requirements(degree_id: str) -> List[str]:
    """
    Get all courses required for a degree.

    Args:
        degree_id: The degree ID to get requirements for.

    Returns:
        List of required course codes.
    """
    cypher = """
    MATCH (c:Course)-[:REQUIRED_FOR]->(d:Degree {degree_id: $degree_id})
    RETURN c.code AS course
    """
    result = get_neo4j_client().query(cypher, {"degree_id": degree_id})
    return [row["course"] for row in result]


def get_completed_courses(student_id: str) -> List[str]:
    """
    Get all courses a student has completed.

    Args:
        student_id: The student ID to get completed courses for.

    Returns:
        List of completed course codes.
    """
    cypher = """
    MATCH (s:Student {student_id: $student_id})-[:HAS_COMPLETED]->(c:Course)
    RETURN c.code AS course
    """
    result = get_neo4j_client().query(cypher, {"student_id": student_id})
    return [row["course"] for row in result]


def get_direct_prereqs(course: str) -> List[str]:
    """
    Get direct prerequisites for a course.

    Args:
        course: The course code to get prerequisites for.

    Returns:
        List of direct prerequisite course codes.
    """
    cypher = """
    MATCH (p:Course)-[:PRE_REQUIRES]->(c:Course {code: $course})
    RETURN p.code AS prereq
    """
    result = get_neo4j_client().query(cypher, {"course": course})
    return [row["prereq"] for row in result]


def degree_topological_sort(courses: List[str]) -> Optional[List[List[str]]]:
    """
    Perform topological sort on courses based on prerequisite dependencies.

    Args:
        courses: List of course codes to sort.

    Returns:
        List of lists, where each inner list contains courses that can be taken
        in the same semester. Returns None if a cycle is detected.
    """
    graph = {c: set(get_direct_prereqs(c)) for c in courses}

    sequence = []
    remaining = set(courses)

    while remaining:
        # Find courses whose prerequisites are not still missing
        available = [c for c in remaining if not graph[c] & remaining]

        if not available:
            return None  # Cycle detected

        sequence.append(sorted(available))
        remaining -= set(available)

    return sequence


def plan_degree(
    student_id: str, degree_id: str
) -> Dict[str, Union[str, List[str], Optional[List[List[str]]]]]:
    """
    Generate a degree completion plan for a student.

    Args:
        student_id: The student ID to plan for.
        degree_id: The degree ID to plan completion for.

    Returns:
        Dictionary containing:
        - student_id: Student ID
        - degree_id: Degree ID
        - remaining_courses: List of courses still needed
        - recommended_sequence: List of semesters, each containing courses to take
        - warning: Optional warning message if cycle detected
    """
    required = set(get_degree_requirements(degree_id))
    completed = set(get_completed_courses(student_id))

    missing = sorted(required - completed)

    if not missing:
        return {
            "student_id": student_id,
            "degree_id": degree_id,
            "remaining_courses": [],
            "recommended_sequence": [],
        }

    ordered = degree_topological_sort(missing)

    if ordered is None:
        return {
            "student_id": student_id,
            "degree_id": degree_id,
            "remaining_courses": missing,
            "recommended_sequence": None,
            "warning": "Cycle detected in degree requirements",
        }

    return {
        "student_id": student_id,
        "degree_id": degree_id,
        "remaining_courses": missing,
        "recommended_sequence": ordered,
    }
