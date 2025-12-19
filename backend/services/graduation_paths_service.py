"""
Graduation Paths Service

Generates all possible valid graduation paths by enumerating all topological
orderings of remaining courses based on prerequisite dependencies.
"""

from typing import Dict, List, Set, Union

from backend.database.neo4j import get_neo4j_client
from backend.services.degree_planner_service import (
    get_completed_courses,
    get_degree_requirements,
    get_direct_prereqs,
)


def build_graph(courses: List[str]) -> Dict[str, Set[str]]:
    """
    Build a prerequisite dependency graph for courses.

    Args:
        courses: List of course codes to build graph for.

    Returns:
        Dictionary mapping each course to its set of direct prerequisites.
    """
    graph = {c: set(get_direct_prereqs(c)) for c in courses}
    return graph


def all_topological_orders(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Generate all possible topological orderings of courses.

    Uses depth-first search with backtracking to enumerate all valid orderings
    that respect prerequisite dependencies.

    Args:
        graph: Dictionary mapping courses to their prerequisite sets.

    Returns:
        List of all valid course orderings, where each ordering is a list of course codes.
    """
    results: List[List[str]] = []
    visited: Set[str] = set()
    order: List[str] = []

    def dfs() -> None:
        added = False
        for node in graph:
            if node not in visited:
                # Check if all prerequisites are already in order
                if all(p in visited for p in graph[node]):
                    visited.add(node)
                    order.append(node)

                    dfs()

                    # Backtrack
                    visited.remove(node)
                    order.pop()

                    added = True

        if not added:
            # Completed valid ordering
            results.append(order.copy())

    dfs()
    return results


def generate_graduation_paths(
    student_id: str
) -> Dict[str, Union[str, List[str], List[List[str]]]]:
    """
    Generate all possible graduation paths for a student.

    Args:
        student_id: The student ID to generate paths for.

    Returns:
        Dictionary containing:
        - student_id: Student ID
        - degree_id: Degree ID
        - missing_courses: List of courses still needed
        - paths: List of all valid course orderings
        - error: Optional error message if student not found
    """
    client = get_neo4j_client()

    degree_result = client.query(
        """
        MATCH (s:Student {student_id: $sid})-[:ENROLLED_IN]->(d:Degree)
        RETURN d.degree_id AS degree
        """,
        {"sid": student_id},
    )

    if not degree_result:
        return {"error": "Student not found"}

    degree_id = degree_result[0]["degree"]

    # Required courses
    required = set(get_degree_requirements(degree_id))
    completed = set(get_completed_courses(student_id))
    missing = sorted(required - completed)

    if not missing:
        return {"student_id": student_id, "degree_id": degree_id, "paths": [["Already graduated"]]}

    # Build dependency graph
    graph = build_graph(missing)

    # Enumerate all valid paths
    paths = all_topological_orders(graph)

    return {
        "student_id": student_id,
        "degree_id": degree_id,
        "missing_courses": missing,
        "paths": paths,
    }
