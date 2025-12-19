"""
Unit tests for degree planner service
"""
import pytest
from backend.services.degree_planner_service import (
    get_degree_requirements,
    get_completed_courses,
    get_direct_prereqs,
    degree_topological_sort,
    plan_degree,
)


class MockNeo4jClient:
    def __init__(self, results_map):
        self._results_map = results_map

    def query(self, query, params=None, read_only=True):
        # Simple mock - return based on query content
        if "REQUIRED_FOR" in query:
            return self._results_map.get("degree_requirements", [])
        elif "HAS_COMPLETED" in query:
            return self._results_map.get("completed_courses", [])
        elif "PRE_REQUIRES" in query:
            course = params.get("course") if params else None
            return self._results_map.get("prereqs", {}).get(course, [])
        return []


@pytest.fixture
def mock_client(monkeypatch):
    def _mock(results_map):
        from backend.services import degree_planner_service
        monkeypatch.setattr(
            degree_planner_service,
            "get_neo4j_client",
            lambda: MockNeo4jClient(results_map),
        )
    return _mock


def test_get_degree_requirements(mock_client):
    """Test getting degree requirements"""
    mock_client({
        "degree_requirements": [
            {"course": "CS101"},
            {"course": "CS102"},
            {"course": "MATH101"},
        ]
    })
    
    result = get_degree_requirements("CS")
    assert sorted(result) == ["CS101", "CS102", "MATH101"]


def test_get_completed_courses(mock_client):
    """Test getting completed courses"""
    mock_client({
        "completed_courses": [
            {"course": "CS101"},
            {"course": "MATH101"},
        ]
    })
    
    result = get_completed_courses("S1")
    assert sorted(result) == ["CS101", "MATH101"]


def test_get_direct_prereqs(mock_client):
    """Test getting direct prerequisites"""
    mock_client({
        "prereqs": {
            "CS102": [{"prereq": "CS101"}],
            "CS103": [{"prereq": "CS101"}, {"prereq": "CS102"}],
        }
    })
    
    result = get_direct_prereqs("CS102")
    assert result == ["CS101"]


def test_degree_topological_sort_simple(mock_client):
    """Test topological sort with simple dependencies"""
    mock_client({
        "prereqs": {
            "CS102": [{"prereq": "CS101"}],
            "CS103": [{"prereq": "CS102"}],
        }
    })
    
    result = degree_topological_sort(["CS101", "CS102", "CS103"])
    assert result is not None
    assert len(result) == 3
    assert result[0] == ["CS101"]  # No prerequisites


def test_degree_topological_sort_no_deps(mock_client):
    """Test topological sort with no dependencies"""
    mock_client({"prereqs": {}})
    
    result = degree_topological_sort(["CS101", "CS102"])
    assert result is not None
    assert len(result) == 1  # All can be taken together


def test_plan_degree_all_completed(mock_client):
    """Test planning when all courses are completed"""
    mock_client({
        "degree_requirements": [{"course": "CS101"}],
        "completed_courses": [{"course": "CS101"}],
        "prereqs": {},
    })
    
    result = plan_degree("S1", "CS")
    assert result["remaining_courses"] == []
    assert result["recommended_sequence"] == []


def test_plan_degree_with_remaining(mock_client):
    """Test planning with remaining courses"""
    mock_client({
        "degree_requirements": [
            {"course": "CS101"},
            {"course": "CS102"},
        ],
        "completed_courses": [{"course": "CS101"}],
        "prereqs": {
            "CS102": [{"prereq": "CS101"}],
        },
    })
    
    result = plan_degree("S1", "CS")
    assert "CS102" in result["remaining_courses"]
    assert result["recommended_sequence"] is not None

