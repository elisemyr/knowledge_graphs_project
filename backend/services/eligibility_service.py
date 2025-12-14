from typing import List
from backend.models.eligibility import EligibilityResponse
from backend.database.neo4j import get_neo4j_client


class EligibilityService:

    def __init__(self):
        """Initialize with a Neo4j client connection."""
        self.client = get_neo4j_client()

    def get_completed_courses(self, student_id: str) -> List[str]:
        """
        Fetch all courses a student has completed from Neo4j.
        """
        query = """
        MATCH (s:Student {student_id: $student_id})-[:HAS_COMPLETED]->(c:Course)
        RETURN c.code AS code
        ORDER BY code
        """
        results = self.client.query(query, {"student_id": student_id}, read_only=True)
        return [r["code"] for r in results]

    def compute_missing_prerequisites(
        self,
        course_prereqs: List[str],
        completed_courses: List[str]
    ) -> List[str]:
        """
        Returns a list of prerequisites the student has NOT completed.
        """
        return [pr for pr in course_prereqs if pr not in completed_courses]

    def create_eligibility_response(
        self,
        student_id: str,
        course_id: str,
        missing: List[str]
    ) -> EligibilityResponse:
        """
        Build the structured response model.
        """
        return EligibilityResponse(
            student_id=student_id,
            course_id=course_id,
            eligible=(len(missing) == 0),
            missing_prerequisites=missing
        )
