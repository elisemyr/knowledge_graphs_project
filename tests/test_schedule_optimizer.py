"""
Tests for Schedule Optimization API
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_optimize_schedule_endpoint_exists():
    """
    Test that the schedule optimization endpoint exists and returns 200
    """
    response = client.get("/api/students/S001/schedule/optimize")
    assert response.status_code == 200


def test_optimize_schedule_returns_correct_structure():
    """
    Test that the optimization returns the expected response structure
    """
    response = client.get("/api/students/S001/schedule/optimize")
    assert response.status_code == 200
    
    data = response.json()
    
    # Check top-level keys
    assert "student_id" in data
    assert "schedule" in data
    assert "total_semesters" in data
    assert "total_courses" in data
    assert "completed_courses" in data
    
    # Check schedule structure
    assert isinstance(data["schedule"], list)
    if len(data["schedule"]) > 0:
        semester = data["schedule"][0]
        assert "semester_id" in semester
        assert "semester_name" in semester
        assert "courses" in semester
        assert "total_courses" in semester


def test_optimize_schedule_with_parameters():
    """
    Test schedule optimization with custom parameters
    """
    response = client.get(
        "/api/students/S001/schedule/optimize",
        params={
            "max_courses_per_semester": 4,
            "target_semesters": 6,
            "start_semester": "FALL_2024"
        }
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["student_id"] == "S001"
    
    # Verify no semester has more than 4 courses
    for semester in data["schedule"]:
        assert semester["total_courses"] <= 4


def test_optimize_schedule_respects_max_courses():
    """
    Test that schedule respects max_courses_per_semester constraint
    """
    max_courses = 3
    response = client.get(
        "/api/students/S002/schedule/optimize",
        params={"max_courses_per_semester": max_courses}
    )
    assert response.status_code == 200
    
    data = response.json()
    
    for semester in data["schedule"]:
        assert semester["total_courses"] <= max_courses


def test_optimize_schedule_includes_completed_courses():
    """
    Test that the response includes completed courses
    """
    response = client.get("/api/students/S001/schedule/optimize")
    assert response.status_code == 200
    
    data = response.json()
    assert "completed_courses" in data
    assert isinstance(data["completed_courses"], list)


def test_get_available_semesters():
    """
    Test the semesters listing endpoint
    """
    response = client.get("/api/students/S001/schedule/semesters")
    assert response.status_code == 200
    
    data = response.json()
    assert "semesters" in data
    assert "total" in data
    assert isinstance(data["semesters"], list)


def test_available_semesters_with_limit():
    """
    Test semesters endpoint with limit parameter
    """
    limit = 4
    response = client.get(
        "/api/students/S001/schedule/semesters",
        params={"limit": limit}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["semesters"]) <= limit


def test_schedule_for_nonexistent_student():
    """
    Test scheduling for a student that doesn't exist
    Should still return 200 but with empty/default data
    """
    response = client.get("/api/students/NONEXISTENT/schedule/optimize")
    # Should handle gracefully - either 200 with empty schedule or 404
    assert response.status_code in [200, 404]


def test_schedule_optimization_warnings():
    """
    Test that warnings are included when appropriate
    """
    response = client.get("/api/students/S003/schedule/optimize")
    assert response.status_code == 200
    
    data = response.json()
    assert "warnings" in data
    assert isinstance(data["warnings"], list)


def test_course_has_prerequisites_in_schedule():
    """
    Test that courses in schedule include prerequisite information
    """
    response = client.get("/api/students/S001/schedule/optimize")
    assert response.status_code == 200
    
    data = response.json()
    
    # Check that courses have prerequisite field
    for semester in data["schedule"]:
        for course in semester["courses"]:
            assert "course_code" in course
            assert "course_name" in course
            assert "prerequisites" in course
            assert isinstance(course["prerequisites"], list)