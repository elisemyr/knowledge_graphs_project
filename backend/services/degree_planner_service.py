from backend.database.neo4j import get_neo4j_client


def get_degree_requirements(degree_id: str):
    cypher = """
    MATCH (c:Course)-[:REQUIRED_FOR]->(d:Degree {degree_id: $degree_id})
    RETURN c.code AS course
    """
    result = get_neo4j_client().query(cypher, {"degree_id": degree_id})
    return [row["course"] for row in result]


def get_completed_courses(student_id: str):
    cypher = """
    MATCH (s:Student {student_id: $student_id})-[:HAS_COMPLETED]->(c:Course)
    RETURN c.code AS course
    """
    result = get_neo4j_client().query(cypher, {"student_id": student_id})
    return [row["course"] for row in result]


def get_direct_prereqs(course: str):
    cypher = """
    MATCH (p:Course)-[:PRE_REQUIRES]->(c:Course {code: $course})
    RETURN p.code AS prereq
    """
    result = get_neo4j_client().query(cypher, {"course": course})
    return [row["prereq"] for row in result]


def degree_topological_sort(courses: list[str]):
    # build graph
    graph = {c: set(get_direct_prereqs(c)) for c in courses}

    sequence = []
    remaining = set(courses)

    while remaining:
        # find courses whose prereqs are not still missing
        available = [c for c in remaining if not (graph[c] & remaining)]

        if not available:
            return None  # cycle detected

        sequence.append(sorted(available))
        remaining -= set(available)

    return sequence


def plan_degree(student_id: str, degree_id: str):
    required = set(get_degree_requirements(degree_id))
    completed = set(get_completed_courses(student_id))

    missing = sorted(required - completed)

    if not missing:
        return {
            "student_id": student_id,
            "degree_id": degree_id,
            "remaining_courses": [],
            "recommended_sequence": []
        }

    ordered = degree_topological_sort(missing)

    if ordered is None:
        return {
            "student_id": student_id,
            "degree_id": degree_id,
            "remaining_courses": missing,
            "recommended_sequence": None,
            "warning": "Cycle detected in degree requirements"
        }

    return {
        "student_id": student_id,
        "degree_id": degree_id,
        "remaining_courses": missing,
        "recommended_sequence": ordered
    }
