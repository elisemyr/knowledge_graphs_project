from typing import List, Set
from backend.services.degree_planner_service import (
    get_degree_requirements, 
    get_completed_courses,
    get_direct_prereqs
)


def build_graph(courses: List[str]):
    graph = {c: set(get_direct_prereqs(c)) for c in courses}
    return graph


def all_topological_orders(graph):
    results = []
    visited = set()
    order = []

    def dfs():
        added = False
        for node in graph:
            if node not in visited:
                # Check if all prerequisites are already in order
                if all(p in visited for p in graph[node]):
                    visited.add(node)
                    order.append(node)

                    dfs()

                    # backtrack
                    visited.remove(node)
                    order.pop()

                    added = True

        if not added:
            # Completed valid ordering
            results.append(order.copy())

    dfs()
    return results


def generate_graduation_paths(student_id: str):
    # Determine student degree
    from backend.database.neo4j import get_neo4j_client
    client = get_neo4j_client()

    degree_result = client.query("""
        MATCH (s:Student {student_id: $sid})-[:ENROLLED_IN]->(d:Degree)
        RETURN d.degree_id AS degree
    """, {"sid": student_id})

    if not degree_result:
        return {"error": "Student not found"}

    degree_id = degree_result[0]["degree"]

    # Required courses
    required = set(get_degree_requirements(degree_id))
    completed = set(get_completed_courses(student_id))
    missing = sorted(required - completed)

    if not missing:
        return {
            "student_id": student_id,
            "degree_id": degree_id,
            "paths": [["Already graduated"]]
        }

    # Build dependency graph
    graph = build_graph(missing)

    # Enumerate all valid paths
    paths = all_topological_orders(graph)

    return {
        "student_id": student_id,
        "degree_id": degree_id,
        "missing_courses": missing,
        "paths": paths
    }
