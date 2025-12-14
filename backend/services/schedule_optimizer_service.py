"""
Schedule Optimization Service
Uses topological sorting and semester constraints to create optimal course schedules
"""
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, deque
from backend.database.neo4j import get_neo4j_client
from backend.models.schedule import (
    OptimizedScheduleResponse,
    SemesterSchedule,
    CourseInSchedule,
    ScheduleConstraints
)


class ScheduleOptimizerService:
    """Service for optimizing student course schedules"""
    
    def __init__(self):
        self.driver = get_neo4j_client()
    
    def optimize_schedule(
        self,
        student_id: str,
        constraints: ScheduleConstraints
    ) -> OptimizedScheduleResponse:
        """
        Create an optimized course schedule for a student
        
        Args:
            student_id: Student ID
            constraints: Scheduling constraints
            
        Returns:
            OptimizedScheduleResponse with semester-by-semester schedule
        """
        with self.driver.session() as session:
            # 1. Get student info and completed courses
            student_info = self._get_student_info(session, student_id)
            completed_courses = student_info["completed"]
            
            # 2. Get all available courses and their prerequisites
            all_courses = self._get_all_courses_with_prereqs(session)
            
            # 3. Filter out completed courses
            remaining_courses = {
                code: data for code, data in all_courses.items()
                if code not in completed_courses
            }
            
            # 4. Get semester offerings
            semester_offerings = self._get_semester_offerings(
                session,
                constraints.start_semester,
                constraints.target_semesters
            )
            
            # 5. Build prerequisite graph
            prereq_graph = self._build_prereq_graph(remaining_courses, completed_courses)
            
            # 6. Topologically sort courses
            sorted_courses = self._topological_sort(
                prereq_graph,
                remaining_courses,
                completed_courses
            )
            
            # 7. Assign courses to semesters
            schedule = self._assign_courses_to_semesters(
                sorted_courses,
                remaining_courses,
                semester_offerings,
                constraints,
                completed_courses
            )
            
            # 8. Build response
            return self._build_response(
                student_id,
                student_info,
                schedule,
                completed_courses
            )
    
    def _get_student_info(self, session, student_id: str) -> Dict:
        """Get student information and completed courses"""
        query = """
        MATCH (s:Student {id: $student_id})
        OPTIONAL MATCH (s)-[:HAS_COMPLETED]->(c:Course)
        RETURN s.name as name,
               s.program as program,
               collect(c.code) as completed
        """
        result = session.run(query, student_id=student_id)
        record = result.single()
        
        if not record:
            return {
                "name": None,
                "program": None,
                "completed": []
            }
        
        return {
            "name": record["name"],
            "program": record["program"],
            "completed": [c for c in record["completed"] if c]
        }
    
    def _get_all_courses_with_prereqs(self, session) -> Dict[str, Dict]:
        """Get all courses with their prerequisites and metadata"""
        query = """
        MATCH (c:Course)
        OPTIONAL MATCH (c)-[:PRE_REQUIRES]->(prereq:Course)
        RETURN c.code as code,
               c.name as name,
               c.credits as credits,
               collect(prereq.code) as prerequisites
        """
        result = session.run(query)
        
        courses = {}
        for record in result:
            courses[record["code"]] = {
                "name": record["name"],
                "credits": record["credits"] or 3,  # Default 3 credits
                "prerequisites": [p for p in record["prerequisites"] if p]
            }
        
        return courses
    
    def _get_semester_offerings(
        self,
        session,
        start_semester: str,
        num_semesters: int
    ) -> List[Dict]:
        """Get ordered list of semesters with course offerings"""
        query = """
        MATCH (s:Semester)
        WHERE s.id >= $start_semester
        OPTIONAL MATCH (c:Course)-[:OFFERED_IN]->(s)
        WITH s, collect(c.code) as courses
        RETURN s.id as id,
               s.name as name,
               s.year as year,
               s.term as term,
               s.order as order,
               courses
        ORDER BY s.order
        LIMIT $num_semesters
        """
        result = session.run(
            query,
            start_semester=start_semester,
            num_semesters=num_semesters
        )
        
        semesters = []
        for record in result:
            semesters.append({
                "id": record["id"],
                "name": record["name"],
                "year": record["year"],
                "term": record["term"],
                "order": record["order"],
                "courses": [c for c in record["courses"] if c]
            })
        
        return semesters
    
    def _build_prereq_graph(
        self,
        courses: Dict[str, Dict],
        completed: List[str]
    ) -> Dict[str, Set[str]]:
        """
        Build prerequisite dependency graph
        Returns: {course_code: set(courses_that_depend_on_it)}
        """
        graph = defaultdict(set)
        
        for course_code, course_data in courses.items():
            prereqs = course_data["prerequisites"]
            
            # Filter prerequisites to only include uncompleted ones
            uncompleted_prereqs = [
                p for p in prereqs
                if p not in completed and p in courses
            ]
            
            # Add edges: prereq -> course
            for prereq in uncompleted_prereqs:
                graph[prereq].add(course_code)
            
            # Ensure all courses are in the graph
            if course_code not in graph:
                graph[course_code] = set()
        
        return graph
    
    def _topological_sort(
        self,
        graph: Dict[str, Set[str]],
        courses: Dict[str, Dict],
        completed: List[str]
    ) -> List[str]:
        """
        Topological sort using Kahn's algorithm
        Returns courses in order they can be taken
        """
        # Calculate in-degree (number of prerequisites) for each course
        in_degree = defaultdict(int)
        for course_code in courses.keys():
            prereqs = courses[course_code]["prerequisites"]
            # Only count uncompleted prerequisites
            uncompleted_prereqs = [
                p for p in prereqs
                if p not in completed and p in courses
            ]
            in_degree[course_code] = len(uncompleted_prereqs)
        
        # Queue of courses with no prerequisites
        queue = deque([
            course for course, degree in in_degree.items()
            if degree == 0
        ])
        
        sorted_courses = []
        
        while queue:
            course = queue.popleft()
            sorted_courses.append(course)
            
            # Reduce in-degree for dependent courses
            for dependent in graph[course]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Check for cycles (courses not included in sort)
        if len(sorted_courses) != len(courses):
            # Some courses couldn't be sorted (cycle detected)
            # Add remaining courses anyway
            remaining = set(courses.keys()) - set(sorted_courses)
            sorted_courses.extend(remaining)
        
        return sorted_courses
    
    def _assign_courses_to_semesters(
        self,
        sorted_courses: List[str],
        courses: Dict[str, Dict],
        semesters: List[Dict],
        constraints: ScheduleConstraints,
        completed: List[str]
    ) -> List[SemesterSchedule]:
        """
        Assign courses to semesters respecting constraints
        """
        schedule = []
        courses_taken = set(completed)
        
        for semester in semesters:
            semester_courses = []
            semester_credits = 0
            
            # Available courses for this semester
            courses_to_consider = []
            
            for course_code in sorted_courses:
                if course_code in courses_taken:
                    continue
                
                course_data = courses[course_code]
                
                # Check if course is offered this semester
                if course_code not in semester["courses"]:
                    continue
                
                # Check if all prerequisites are met
                prereqs = course_data["prerequisites"]
                if all(p in courses_taken or p in completed for p in prereqs):
                    courses_to_consider.append(course_code)
            
            # Add courses up to constraints
            for course_code in courses_to_consider:
                if len(semester_courses) >= constraints.max_courses_per_semester:
                    break
                
                course_data = courses[course_code]
                credits = course_data["credits"]
                
                if semester_credits + credits > constraints.max_credits_per_semester:
                    continue
                
                semester_courses.append(
                    CourseInSchedule(
                        course_code=course_code,
                        course_name=course_data["name"],
                        credits=credits,
                        prerequisites=course_data["prerequisites"]
                    )
                )
                semester_credits += credits
                courses_taken.add(course_code)
            
            # Create semester schedule
            schedule.append(
                SemesterSchedule(
                    semester_id=semester["id"],
                    semester_name=semester["name"],
                    year=semester["year"],
                    term=semester["term"],
                    courses=semester_courses,
                    total_courses=len(semester_courses),
                    total_credits=semester_credits
                )
            )
        
        return schedule
    
    def _build_response(
        self,
        student_id: str,
        student_info: Dict,
        schedule: List[SemesterSchedule],
        completed: List[str]
    ) -> OptimizedScheduleResponse:
        """Build the final response"""
        total_courses = sum(sem.total_courses for sem in schedule)
        
        warnings = []
        if not schedule:
            warnings.append("No semesters available for scheduling")
        
        # Check for empty semesters
        empty_semesters = [s.semester_name for s in schedule if s.total_courses == 0]
        if empty_semesters:
            warnings.append(f"Empty semesters: {', '.join(empty_semesters)}")
        
        return OptimizedScheduleResponse(
            student_id=student_id,
            student_name=student_info["name"],
            program=student_info["program"],
            schedule=schedule,
            total_semesters=len(schedule),
            total_courses=total_courses,
            completed_courses=completed,
            warnings=warnings
        )


# Singleton instance
_schedule_optimizer_service = None

def get_schedule_optimizer_service() -> ScheduleOptimizerService:
    """Get or create schedule optimizer service instance"""
    global _schedule_optimizer_service
    if _schedule_optimizer_service is None:
        _schedule_optimizer_service = ScheduleOptimizerService()
    return _schedule_optimizer_service