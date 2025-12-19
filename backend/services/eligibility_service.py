"""
Eligibility Service

Service for checking student eligibility for courses based on completed prerequisites.
"""

from typing import List

from backend.database.neo4j import get_neo4j_client
from backend.models.eligibility import EligibilityResponse


class EligibilityService:
    """Service for checking student course eligibility."""

    def __init__(self) -> None:
        """
        Initialize with a Neo4j client connection.
        """
        self.client = get_neo4j_client()

    def get_completed_courses(self, student_id: str) -> List[str]:
        """
        Fetch all courses a student has completed from Neo4j.

        Args:
            student_id: The student ID to fetch completed courses for.

        Returns:
            List of completed course codes, sorted alphabetically.
        """
        query = """
        MATCH (s:Student {student_id: $student_id})-[:HAS_COMPLETED]->(c:Course)
        RETURN c.code AS code
        ORDER BY code
        """
        results = self.client.query(query, {"student_id": student_id}, read_only=True)
        return [r["code"] for r in results]

    def compute_missing_prerequisites(self, course_prereqs: List[str], completed_courses: List[str]) -> List[str]:
        """
        Compute which prerequisites the student has NOT completed.

        Args:
            course_prereqs: List of all prerequisite course codes required.
            completed_courses: List of course codes the student has completed.

        Returns:
            List of prerequisite course codes that are missing.
        """
        return [pr for pr in course_prereqs if pr not in completed_courses]

    def create_eligibility_response(
        self, student_id: str, course_id: str, missing: List[str]
    ) -> EligibilityResponse:
        """
        Build the structured eligibility response model.

        Args:
            student_id: The student ID.
            course_id: The course code being checked.
            missing: List of missing prerequisite course codes.

        Returns:
            EligibilityResponse model with eligibility status and missing prerequisites.
        """
        return EligibilityResponse(
            student_id=student_id,
            course_id=course_id,
            eligible=(len(missing) == 0),
            missing_prerequisites=missing
        )
