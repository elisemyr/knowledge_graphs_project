"""
Moderate Complexity Cypher Queries Service
Practical queries for school context with advanced patterns
"""

from typing import List, Dict, Any
from backend.database.neo4j import get_neo4j_driver


class ModerateQueriesService:
    """
    Service for moderate complexity queries with practical school applications.

    Provides advanced Cypher query patterns for bottleneck detection,
    course recommendations, and student progress analysis.
    """

    def __init__(self) -> None:
        """
        Initialize the moderate queries service.

        Creates a Neo4j driver connection for executing complex queries.
        """
        self.driver = get_neo4j_driver()

    def find_bottleneck_courses(
        self, min_dependents: int = 3, min_prerequisites: int = 2, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find "bottleneck" courses that many students need but have difficult prerequisites.

        These are critical courses that:
        - Unlock many other courses (high dependent count)
        - Require multiple prerequisites themselves

        Advanced patterns:
        - OPTIONAL MATCH with multiple patterns
        - Variable-length paths: *1..3
        - Multiple WITH clauses
        - Aggregation: count(), collect()

        Args:
            min_dependents: Minimum number of courses this must unlock
            min_prerequisites: Minimum prerequisites required
            limit: Maximum results to return

        Returns:
            List of bottleneck courses with metrics
        """
        with self.driver.session() as session:
            query = """
            // Find courses that block progress
            MATCH (bottleneck:Course)
            
            // Count courses that require this course
            OPTIONAL MATCH (dependent:Course)-[:PRE_REQUIRES]->(bottleneck)
            WITH bottleneck, count(DISTINCT dependent) as courses_this_unlocks
            
            // Count prerequisites for this course (depth 1-3)
            OPTIONAL MATCH (bottleneck)-[:PRE_REQUIRES*1..3]->(prereq:Course)
            WITH bottleneck, 
                 courses_this_unlocks,
                 count(DISTINCT prereq) as total_prereqs
            
            // Filter for bottlenecks
            WHERE courses_this_unlocks >= $min_dependents 
              AND total_prereqs >= $min_prerequisites
            
            // Get semester availability
            OPTIONAL MATCH (bottleneck)-[:OFFERED_IN]->(sem:Semester)
            WITH bottleneck,
                 courses_this_unlocks,
                 total_prereqs,
                 collect(DISTINCT sem.name) as offered_semesters
            
            RETURN bottleneck.code as course_code,
                   bottleneck.name as course_name,
                   total_prereqs as prerequisites_needed,
                   courses_this_unlocks as courses_unlocked,
                   size(offered_semesters) as semesters_offered,
                   offered_semesters[0..3] as sample_semesters
            ORDER BY courses_this_unlocks DESC, total_prereqs DESC
            LIMIT $limit
            """

            result = session.run(query, min_dependents=min_dependents, min_prerequisites=min_prerequisites, limit=limit)

            courses = []
            for record in result:
                courses.append(
                    {
                        "course_code": record["course_code"],
                        "course_name": record["course_name"],
                        "prerequisites_needed": record["prerequisites_needed"],
                        "courses_unlocked": record["courses_unlocked"],
                        "semesters_offered": record["semesters_offered"],
                        "sample_semesters": record["sample_semesters"],
                        "bottleneck_score": record["courses_unlocked"] * 2 + record["prerequisites_needed"],
                    }
                )

            return courses

    def get_course_recommendations(
        self, student_id: str, semester_id: str, min_readiness: int = 75, limit: int = 15
    ) -> Dict[str, Any]:
        """
        Get personalized course recommendations for a student for a specific semester.

        Calculates a "readiness score" based on:
        - How many prerequisites are complete
        - How many courses this will unlock

        Advanced patterns:
        - Multiple OPTIONAL MATCH patterns
        - List comprehension with filtering
        - Complex CASE expressions
        - Computed metrics (readiness score)

        Args:
            student_id: Student ID
            semester_id: Target semester (e.g., 'FALL_2024')
            min_readiness: Minimum readiness score (0-100)
            limit: Maximum courses to return

        Returns:
            Dict with student info and recommended courses
        """
        with self.driver.session() as session:
            query = """
            // Get student and completed courses
            MATCH (student:Student {id: $student_id})
            OPTIONAL MATCH (student)-[:HAS_COMPLETED]->(completed:Course)
            WITH student, collect(DISTINCT completed.code) as completed_codes
            
            // Find courses offered in target semester that aren't completed
            MATCH (available:Course)-[:OFFERED_IN]->(sem:Semester {id: $semester_id})
            WHERE NOT available.code IN completed_codes
            
            // Check prerequisites for each course
            OPTIONAL MATCH (available)-[:PRE_REQUIRES]->(prereq:Course)
            WITH student,
                 available,
                 completed_codes,
                 collect(DISTINCT prereq.code) as required_prereqs
            
            // Calculate missing prerequisites
            WITH student,
                 available,
                 required_prereqs,
                 [p IN required_prereqs WHERE NOT p IN completed_codes] as missing_prereqs
            
            // Count courses this would unlock
            OPTIONAL MATCH (future:Course)-[:PRE_REQUIRES]->(available)
            WITH student,
                 available,
                 required_prereqs,
                 missing_prereqs,
                 count(DISTINCT future) as unlocks_count
            
            // Calculate readiness score (0-100)
            WITH student,
                 available,
                 size(required_prereqs) as total_prereqs,
                 size(missing_prereqs) as missing_count,
                 unlocks_count,
                 CASE 
                     WHEN size(required_prereqs) = 0 THEN 100
                     WHEN size(missing_prereqs) = 0 THEN 100
                     ELSE toInteger(100.0 * (1.0 - toFloat(size(missing_prereqs)) / toFloat(size(required_prereqs))))
                 END as readiness_score
            
            // Filter by minimum readiness
            WHERE readiness_score >= $min_readiness
            
            RETURN available.code as course_code,
                   available.name as course_name,
                   available.credits as credits,
                   readiness_score,
                   missing_count as prerequisites_missing,
                   unlocks_count as future_courses_unlocked,
                   CASE 
                       WHEN readiness_score = 100 THEN 'Ready Now'
                       WHEN readiness_score >= 75 THEN 'Almost Ready'
                       ELSE 'Not Ready'
                   END as status
            ORDER BY readiness_score DESC, unlocks_count DESC
            LIMIT $limit
            """

            result = session.run(
                query, student_id=student_id, semester_id=semester_id, min_readiness=min_readiness, limit=limit
            )

            # Get student info
            student_query = """
            MATCH (s:Student {id: $student_id})
            RETURN s.name as name, s.program as program
            """
            student_result = session.run(student_query, student_id=student_id)
            student_record = student_result.single()

            courses = []
            for record in result:
                courses.append(
                    {
                        "course_code": record["course_code"],
                        "course_name": record["course_name"],
                        "credits": record["credits"] or 3,
                        "readiness_score": record["readiness_score"],
                        "prerequisites_missing": record["prerequisites_missing"],
                        "future_courses_unlocked": record["future_courses_unlocked"],
                        "status": record["status"],
                    }
                )

            return {
                "student_id": student_id,
                "student_name": student_record["name"] if student_record else None,
                "program": student_record["program"] if student_record else None,
                "semester_id": semester_id,
                "recommendations": courses,
                "total_recommendations": len(courses),
            }

    def get_courses_by_prerequisite_depth(self, student_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        Show remaining courses organized by prerequisite depth.

        Helps students see which courses they can take sooner vs later.

        Advanced patterns:
        - List comprehension with WHERE filtering
        - Variable-length paths with bounds: *1..5
        - max(length(path)) aggregation
        - Multiple WITH clauses
        - CASE expressions

        Args:
            student_id: Student ID
            limit: Maximum courses to return

        Returns:
            Dict with courses organized by readiness
        """
        with self.driver.session() as session:
            query = """
            // Get student and completed courses
            MATCH (student:Student {id: $student_id})
            OPTIONAL MATCH (student)-[:HAS_COMPLETED]->(completed:Course)
            WITH student, collect(DISTINCT completed.code) as completed_codes
            
            // Find remaining courses
            MATCH (remaining:Course)
            WHERE NOT remaining.code IN completed_codes
            
            // Count direct prerequisites
            OPTIONAL MATCH (remaining)-[:PRE_REQUIRES]->(direct_prereq:Course)
            WITH student,
                 remaining,
                 completed_codes,
                 collect(DISTINCT direct_prereq.code) as direct_prereqs
            
            // Calculate missing direct prerequisites
            WITH student,
                 remaining,
                 direct_prereqs,
                 [p IN direct_prereqs WHERE NOT p IN completed_codes] as missing_prereqs
            
            // Get maximum depth of prerequisite chain (limited to 5)
            OPTIONAL MATCH path = (remaining)-[:PRE_REQUIRES*1..5]->(deep_prereq:Course)
            WHERE NOT deep_prereq.code IN completed_codes
            WITH student,
                 remaining,
                 size(direct_prereqs) as total_direct_prereqs,
                 size(missing_prereqs) as missing_direct_prereqs,
                 CASE 
                     WHEN count(path) = 0 THEN 0
                     ELSE max(length(path))
                 END as max_depth
            
            // Get semester availability
            OPTIONAL MATCH (remaining)-[:OFFERED_IN]->(sem:Semester)
            WITH remaining,
                 total_direct_prereqs,
                 missing_direct_prereqs,
                 max_depth,
                 count(DISTINCT sem) as semesters_offered
            
            // Only show courses with prerequisites
            WHERE total_direct_prereqs > 0
            
            RETURN remaining.code as course_code,
                   remaining.name as course_name,
                   total_direct_prereqs as total_prerequisites,
                   missing_direct_prereqs as prerequisites_missing,
                   max_depth as chain_depth,
                   semesters_offered,
                   CASE 
                       WHEN missing_direct_prereqs = 0 THEN 'Ready Now'
                       WHEN missing_direct_prereqs <= 1 THEN 'Almost Ready'
                       WHEN missing_direct_prereqs <= 2 THEN 'Plan Soon'
                       ELSE 'Plan Later'
                   END as recommendation
            ORDER BY missing_direct_prereqs ASC, max_depth ASC, course_code
            LIMIT $limit
            """

            result = session.run(query, student_id=student_id, limit=limit)

            # Get student info
            student_query = """
            MATCH (s:Student {id: $student_id})
            OPTIONAL MATCH (s)-[:HAS_COMPLETED]->(c:Course)
            RETURN s.name as name, 
                   s.program as program,
                   count(c) as completed_count
            """
            student_result = session.run(student_query, student_id=student_id)
            student_record = student_result.single()

            # Organize courses by recommendation
            courses_by_status = {"ready_now": [], "almost_ready": [], "plan_soon": [], "plan_later": []}

            all_courses = []
            for record in result:
                course = {
                    "course_code": record["course_code"],
                    "course_name": record["course_name"],
                    "total_prerequisites": record["total_prerequisites"],
                    "prerequisites_missing": record["prerequisites_missing"],
                    "chain_depth": record["chain_depth"],
                    "semesters_offered": record["semesters_offered"],
                    "recommendation": record["recommendation"],
                }
                all_courses.append(course)

                # Categorize
                status = record["recommendation"].lower().replace(" ", "_")
                if status in courses_by_status:
                    courses_by_status[status].append(course)

            return {
                "student_id": student_id,
                "student_name": student_record["name"] if student_record else None,
                "program": student_record["program"] if student_record else None,
                "completed_courses": student_record["completed_count"] if student_record else 0,
                "courses_by_status": courses_by_status,
                "all_courses": all_courses,
                "total_remaining": len(all_courses),
            }


# Singleton instance
_moderate_queries_service = None


def get_moderate_queries_service() -> ModerateQueriesService:
    """Get or create moderate queries service instance"""
    global _moderate_queries_service
    if _moderate_queries_service is None:
        _moderate_queries_service = ModerateQueriesService()
    return _moderate_queries_service
