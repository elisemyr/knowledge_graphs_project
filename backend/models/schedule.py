"""
Pydantic models for schedule optimization
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CourseInSchedule(BaseModel):
    """A course scheduled in a specific semester"""

    course_code: str = Field(..., description="Course code (e.g., 'CS 101')")
    course_name: str = Field(..., description="Course name")
    credits: Optional[int] = Field(None, description="Credit hours")
    prerequisites: List[str] = Field(
        default_factory=list, description="List of prerequisite course codes"
    )


class SemesterSchedule(BaseModel):
    """Schedule for one semester"""

    semester_id: str = Field(..., description="Semester ID (e.g., 'FALL_2024')")
    semester_name: str = Field(..., description="Human-readable semester name")
    year: int = Field(..., description="Year")
    term: str = Field(..., description="Term (Fall/Spring)")
    courses: List[CourseInSchedule] = Field(
        default_factory=list, description="Courses in this semester"
    )
    total_courses: int = Field(0, description="Total number of courses")
    total_credits: int = Field(0, description="Total credit hours")


class OptimizedScheduleResponse(BaseModel):
    """Response for optimized schedule"""

    student_id: str = Field(..., description="Student ID")
    student_name: Optional[str] = Field(None, description="Student name")
    program: Optional[str] = Field(None, description="Student's program")
    schedule: List[SemesterSchedule] = Field(
        ..., description="Optimized semester-by-semester schedule"
    )
    total_semesters: int = Field(..., description="Total number of semesters")
    total_courses: int = Field(..., description="Total courses in schedule")
    completed_courses: List[str] = Field(
        default_factory=list, description="Courses already completed"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Any scheduling warnings or conflicts"
    )


class ScheduleConstraints(BaseModel):
    """Constraints for schedule optimization"""

    max_courses_per_semester: int = Field(
        5, ge=1, le=8, description="Maximum courses per semester"
    )
    max_credits_per_semester: int = Field(
        18, ge=6, le=24, description="Maximum credit hours per semester"
    )
    target_semesters: Optional[int] = Field(
        8, ge=1, le=12, description="Target number of semesters"
    )
    start_semester: Optional[str] = Field("FALL_2024", description="Starting semester ID")
