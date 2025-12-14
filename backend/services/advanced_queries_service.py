"""
Advanced Cypher Queries Service

Demonstrates complex Cypher patterns:
- Recursive traversal (depth >= 3)
- OPTIONAL MATCH with complex patterns
- WITH clauses for data transformation
- UNWIND for list processing
- Advanced filtering and aggregation
- Parameter usage throughout
"""
from typing import List, Dict, Any, Optional
from backend.database.neo4j import get_neo4j_driver


class AdvancedQueriesService:
    """Service for advanced Cypher query patterns"""
    
    def __init__(self):
        self.driver = get_neo4j_driver()
    
    # ==================== ADVANCED PATTERN 1 ====================
    # Recursive traversal with depth >= 3, WITH, filtering
    
    def get_deep_prerequisite_chain(
        self,
        course_code: str,
        min_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Find prerequisite chains of depth >= 3 for a course.
        
        Advanced patterns:
        - Variable-length path traversal: [:PRE_REQUIRES*3..]
        - WITH for intermediate aggregation
        - collect() and size() for counting
        - Parameters throughout
        
        Args:
            course_code: Target course code
            min_depth: Minimum chain depth (default 3)
            
        Returns:
            Dict with prerequisite chains organized by depth
        """
        with self.driver.session() as session:
            query = """
            // Start with target course
            MATCH (target:Course {code: $course_code})
            
            // Find paths of depth >= min_depth
            MATCH path = (target)-[:PRE_REQUIRES*3..]->(prereq:Course)
            
            // Use WITH to transform and filter
            WITH target,
                 path,
                 prereq,
                 length(path) as depth,
                 [node IN nodes(path) | node.code] as chain
            WHERE depth >= $min_depth
            
            // Aggregate by depth
            WITH target,
                 depth,
                 collect(DISTINCT {
                     prerequisite: prereq.code,
                     name: prereq.name,
                     full_chain: chain
                 }) as prerequisites_at_depth
            
            // Final aggregation
            RETURN target.code as course,
                   target.name as course_name,
                   collect({
                       depth: depth,
                       count: size(prerequisites_at_depth),
                       prerequisites: prerequisites_at_depth
                   }) as chains_by_depth
            ORDER BY depth
            """
            
            result = session.run(
                query,
                course_code=course_code,
                min_depth=min_depth
            )
            record = result.single()
            
            if not record:
                return {
                    "course": course_code,
                    "found": False,
                    "chains_by_depth": []
                }
            
            return {
                "course": record["course"],
                "course_name": record["course_name"],
                "found": True,
                "chains_by_depth": record["chains_by_depth"]
            }
    
    # ==================== ADVANCED PATTERN 2 ====================
    # OPTIONAL MATCH with complex filtering and UNWIND
    
    def get_next_courses_with_analysis(
        self,
        student_id: str,
        semester_id: str
    ) -> List[Dict[str, Any]]:
        """
        Find courses student can take with detailed prerequisite analysis.
        
        Advanced patterns:
        - Multiple OPTIONAL MATCH clauses
        - UNWIND for list processing
        - Complex WHERE with all() predicate
        - Multiple WITH clauses for data transformation
        - Subquery filtering
        
        Args:
            student_id: Student ID
            semester_id: Target semester ID
            
        Returns:
            List of available courses with prerequisite analysis
        """
        with self.driver.session() as session:
            query = """
            // Get student's completed courses
            MATCH (s:Student {id: $student_id})
            OPTIONAL MATCH (s)-[:HAS_COMPLETED]->(completed:Course)
            WITH s, collect(DISTINCT completed.code) as completed_codes
            
            // Get courses offered in target semester
            MATCH (offered:Course)-[:OFFERED_IN]->(sem:Semester {id: $semester_id})
            WHERE NOT offered.code IN completed_codes
            
            // Get all prerequisites for each offered course
            OPTIONAL MATCH (offered)-[:PRE_REQUIRES*1..]->(prereq:Course)
            WITH s,
                 offered,
                 completed_codes,
                 collect(DISTINCT prereq.code) as all_prereq_codes
            
            // Calculate missing prerequisites
            WITH s,
                 offered,
                 completed_codes,
                 all_prereq_codes,
                 [p IN all_prereq_codes WHERE NOT p IN completed_codes] as missing
            
            // Get direct prerequisites for analysis
            OPTIONAL MATCH (offered)-[:PRE_REQUIRES]->(direct_prereq:Course)
            WITH s,
                 offered,
                 completed_codes,
                 all_prereq_codes,
                 missing,
                 collect(DISTINCT {
                     code: direct_prereq.code,
                     name: direct_prereq.name,
                     completed: direct_prereq.code IN completed_codes
                 }) as direct_prerequisites
            
            // Get courses that depend on this course (future planning)
            OPTIONAL MATCH (future:Course)-[:PRE_REQUIRES*1..2]->(offered)
            WITH s,
                 offered,
                 completed_codes,
                 all_prereq_codes,
                 missing,
                 direct_prerequisites,
                 collect(DISTINCT future.code) as unlocks_courses
            
            // Calculate readiness score
            WITH s,
                 offered,
                 completed_codes,
                 all_prereq_codes,
                 missing,
                 direct_prerequisites,
                 unlocks_courses,
                 CASE 
                     WHEN size(missing) = 0 THEN 100
                     WHEN size(all_prereq_codes) = 0 THEN 100
                     ELSE toInteger(100.0 * (size(all_prereq_codes) - size(missing)) / size(all_prereq_codes))
                 END as readiness_score
            
            // Only return courses that are available or nearly available
            WHERE readiness_score >= 50
            
            // UNWIND for detailed prerequisite analysis
            UNWIND CASE 
                WHEN size(direct_prerequisites) > 0 
                THEN direct_prerequisites 
                ELSE [null] 
            END as prereq_detail
            
            WITH s,
                 offered,
                 readiness_score,
                 missing,
                 unlocks_courses,
                 collect(prereq_detail) as prereq_details
            
            RETURN offered.code as course_code,
                   offered.name as course_name,
                   offered.credits as credits,
                   readiness_score,
                   size(missing) as missing_count,
                   missing as missing_prerequisites,
                   [p IN prereq_details WHERE p IS NOT NULL] as prerequisite_analysis,
                   size(unlocks_courses) as unlocks_count,
                   unlocks_courses[0..5] as sample_unlocked_courses
            ORDER BY readiness_score DESC, course_code
            """
            
            result = session.run(
                query,
                student_id=student_id,
                semester_id=semester_id
            )
            
            courses = []
            for record in result:
                courses.append({
                    "course_code": record["course_code"],
                    "course_name": record["course_name"],
                    "credits": record["credits"],
                    "readiness_score": record["readiness_score"],
                    "can_take_now": record["missing_count"] == 0,
                    "missing_prerequisites": record["missing_prerequisites"],
                    "prerequisite_analysis": record["prerequisite_analysis"],
                    "unlocks": {
                        "count": record["unlocks_count"],
                        "sample_courses": record["sample_unlocked_courses"]
                    }
                })
            
            return courses
    
    # ==================== ADVANCED PATTERN 3 ====================
    # Complex graph analysis with multiple patterns
    
    def analyze_course_difficulty_and_impact(
        self,
        department_prefix: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze course difficulty based on prerequisite depth and impact on other courses.
        
        Advanced patterns:
        - Multiple recursive traversals
        - OPTIONAL MATCH with depth constraints
        - Complex aggregations
        - Conditional logic with CASE
        - Path analysis
        
        Args:
            department_prefix: Filter by department (e.g., "CS", "MATH")
            
        Returns:
            List of courses with difficulty metrics
        """
        with self.driver.session() as session:
            query = """
            // Get all courses (with optional filter)
            MATCH (c:Course)
            WHERE CASE 
                WHEN $dept_prefix IS NOT NULL 
                THEN c.code STARTS WITH $dept_prefix 
                ELSE true 
            END
            
            // Count direct prerequisites
            OPTIONAL MATCH (c)-[:PRE_REQUIRES]->(direct_prereq:Course)
            WITH c, count(DISTINCT direct_prereq) as direct_prereq_count
            
            // Count all prerequisites (depth >= 1)
            OPTIONAL MATCH path1 = (c)-[:PRE_REQUIRES*1..]->(all_prereq:Course)
            WITH c,
                 direct_prereq_count,
                 count(DISTINCT all_prereq) as total_prereq_count,
                 max(length(path1)) as max_prereq_depth
            
            // Count courses that depend on this course (depth >= 1)
            OPTIONAL MATCH path2 = (dependent:Course)-[:PRE_REQUIRES*1..]->(c)
            WITH c,
                 direct_prereq_count,
                 total_prereq_count,
                 max_prereq_depth,
                 count(DISTINCT dependent) as dependent_count,
                 max(length(path2)) as max_dependent_depth
            
            // Find critical path (longest prerequisite chain)
            OPTIONAL MATCH critical_path = (c)-[:PRE_REQUIRES*]->(leaf:Course)
            WHERE NOT (leaf)-[:PRE_REQUIRES]->()
            WITH c,
                 direct_prereq_count,
                 total_prereq_count,
                 max_prereq_depth,
                 dependent_count,
                 max_dependent_depth,
                 critical_path,
                 length(critical_path) as path_length
            ORDER BY path_length DESC
            LIMIT 1
            
            WITH c,
                 direct_prereq_count,
                 total_prereq_count,
                 coalesce(max_prereq_depth, 0) as max_prereq_depth,
                 dependent_count,
                 coalesce(max_dependent_depth, 0) as max_dependent_depth,
                 CASE 
                     WHEN critical_path IS NOT NULL 
                     THEN [node IN nodes(critical_path) | node.code]
                     ELSE []
                 END as critical_chain
            
            // Calculate difficulty score (0-100)
            WITH c,
                 direct_prereq_count,
                 total_prereq_count,
                 max_prereq_depth,
                 dependent_count,
                 max_dependent_depth,
                 critical_chain,
                 (toFloat(total_prereq_count) * 2 + 
                  toFloat(max_prereq_depth) * 10) as difficulty_score
            
            // Calculate impact score (how many courses this unlocks)
            WITH c,
                 direct_prereq_count,
                 total_prereq_count,
                 max_prereq_depth,
                 dependent_count,
                 max_dependent_depth,
                 critical_chain,
                 toInteger(difficulty_score) as difficulty_score,
                 (toFloat(dependent_count) * 2 + 
                  toFloat(max_dependent_depth) * 5) as impact_score
            
            // Determine course type
            WITH c,
                 direct_prereq_count,
                 total_prereq_count,
                 max_prereq_depth,
                 dependent_count,
                 max_dependent_depth,
                 critical_chain,
                 difficulty_score,
                 toInteger(impact_score) as impact_score,
                 CASE
                     WHEN total_prereq_count = 0 AND dependent_count > 5 THEN 'Foundation'
                     WHEN total_prereq_count > 5 AND dependent_count = 0 THEN 'Capstone'
                     WHEN dependent_count > 3 THEN 'Core'
                     WHEN total_prereq_count > 3 THEN 'Advanced'
                     ELSE 'Regular'
                 END as course_type
            
            RETURN c.code as course_code,
                   c.name as course_name,
                   course_type,
                   direct_prereq_count,
                   total_prereq_count,
                   max_prereq_depth,
                   dependent_count,
                   max_dependent_depth,
                   critical_chain,
                   difficulty_score,
                   impact_score
            ORDER BY difficulty_score DESC, impact_score DESC
            """
            
            result = session.run(query, dept_prefix=department_prefix)
            
            courses = []
            for record in result:
                courses.append({
                    "course_code": record["course_code"],
                    "course_name": record["course_name"],
                    "type": record["course_type"],
                    "prerequisites": {
                        "direct": record["direct_prereq_count"],
                        "total": record["total_prereq_count"],
                        "max_depth": record["max_prereq_depth"],
                        "critical_chain": record["critical_chain"]
                    },
                    "dependents": {
                        "count": record["dependent_count"],
                        "max_depth": record["max_dependent_depth"]
                    },
                    "scores": {
                        "difficulty": record["difficulty_score"],
                        "impact": record["impact_score"]
                    }
                })
            
            return courses
    
    # ==================== ADVANCED PATTERN 4 ====================
    # Multi-student comparison with complex aggregation
    
    def compare_student_progress(
        self,
        student_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Compare progress of multiple students with detailed analysis.
        
        Advanced patterns:
        - UNWIND for list processing
        - Multiple OPTIONAL MATCH patterns
        - Complex aggregations with COLLECT
        - WITH for multiple transformation stages
        - Comparative analysis
        
        Args:
            student_ids: List of student IDs to compare
            
        Returns:
            Comparison data for all students
        """
        with self.driver.session() as session:
            query = """
            // UNWIND student IDs for batch processing
            UNWIND $student_ids as student_id
            
            // Get each student
            MATCH (s:Student {id: student_id})
            
            // Get completed courses
            OPTIONAL MATCH (s)-[:HAS_COMPLETED]->(completed:Course)
            WITH s,
                 collect(DISTINCT completed.code) as completed_codes,
                 collect(DISTINCT {
                     code: completed.code,
                     name: completed.name,
                     credits: completed.credits
                 }) as completed_details
            
            // Calculate total credits
            WITH s,
                 completed_codes,
                 completed_details,
                 reduce(total = 0, c IN completed_details | total + coalesce(c.credits, 3)) as total_credits
            
            // Find available courses (prerequisites met)
            MATCH (available:Course)
            WHERE NOT available.code IN completed_codes
            OPTIONAL MATCH (available)-[:PRE_REQUIRES]->(prereq:Course)
            WITH s,
                 completed_codes,
                 completed_details,
                 total_credits,
                 available,
                 collect(prereq.code) as prereqs
            WHERE all(p IN prereqs WHERE p IN completed_codes)
            
            WITH s,
                 completed_codes,
                 completed_details,
                 total_credits,
                 count(DISTINCT available) as available_count,
                 collect(DISTINCT available.code)[0..10] as sample_available
            
            // Find courses blocked by missing prerequisites
            MATCH (blocked:Course)
            WHERE NOT blocked.code IN completed_codes
            OPTIONAL MATCH (blocked)-[:PRE_REQUIRES]->(blocked_prereq:Course)
            WHERE NOT blocked_prereq.code IN completed_codes
            WITH s,
                 completed_codes,
                 completed_details,
                 total_credits,
                 available_count,
                 sample_available,
                 blocked,
                 count(DISTINCT blocked_prereq) as missing_count
            WHERE missing_count > 0
            
            WITH s,
                 completed_codes,
                 completed_details,
                 total_credits,
                 available_count,
                 sample_available,
                 count(DISTINCT blocked) as blocked_count
            
            // Return comprehensive comparison
            RETURN s.id as student_id,
                   s.name as student_name,
                   s.program as program,
                   size(completed_codes) as courses_completed,
                   total_credits,
                   available_count as courses_available,
                   blocked_count as courses_blocked,
                   sample_available,
                   completed_codes[0..5] as sample_completed,
                   toFloat(courses_completed) / (courses_completed + courses_available + courses_blocked) * 100 as progress_percentage
            ORDER BY progress_percentage DESC
            """
            
            result = session.run(query, student_ids=student_ids)
            
            students = []
            for record in result:
                students.append({
                    "student_id": record["student_id"],
                    "student_name": record["student_name"],
                    "program": record["program"],
                    "completed": {
                        "count": record["courses_completed"],
                        "credits": record["total_credits"],
                        "sample": record["sample_completed"]
                    },
                    "available": {
                        "count": record["courses_available"],
                        "sample": record["sample_available"]
                    },
                    "blocked": {
                        "count": record["courses_blocked"]
                    },
                    "progress_percentage": round(record["progress_percentage"], 2)
                })
            
            return {
                "students": students,
                "comparison_count": len(students)
            }


# Singleton instance
_advanced_queries_service = None

def get_advanced_queries_service() -> AdvancedQueriesService:
    """Get or create advanced queries service instance"""
    global _advanced_queries_service
    if _advanced_queries_service is None:
        _advanced_queries_service = AdvancedQueriesService()
    return _advanced_queries_service