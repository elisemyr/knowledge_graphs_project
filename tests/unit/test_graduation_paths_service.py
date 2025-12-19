"""
Unit tests for graduation paths service
"""
import pytest
from backend.services.graduation_paths_service import (
    build_graph,
    all_topological_orders,
    generate_graduation_paths,
)


class MockNeo4jClient:
    def __init__(self, results_map):
        self._results_map = results_map

    def query(self, query, params=None, read_only=True):
        if "ENROLLED_IN" in query:
            return self._results_map.get("student_degree", [])
        elif "REQUIRED_FOR" in query:
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
        from backend.services import graduation_paths_service
        monkeypatch.setattr(
            graduation_paths_service,
            "get_neo4j_client",
            lambda: MockNeo4jClient(results_map),
        )
        # Also mock the imported functions
        from backend.services import degree_planner_service
        monkeypatch.setattr(
            degree_planner_service,
            "get_neo4j_client",
            lambda: MockNeo4jClient(results_map),
        )
    return _mock


def test_build_graph(mock_client):
    """Test building prerequisite graph"""
    mock_client({
        "prereqs": {
            "CS102": [{"prereq": "CS101"}],
            "CS103": [{"prereq": "CS102"}],
        }
    })
    
    from backend.services.degree_planner_service import get_direct_prereqs
    graph = build_graph(["CS101", "CS102", "CS103"])
    assert "CS101" in graph
    assert "CS102" in graph
    assert "CS103" in graph


def test_all_topological_orders_simple():
    """Test generating all topological orders for simple graph"""
    graph = {
        "CS101": set(),
        "CS102": {"CS101"},
    }
    
    orders = all_topological_orders(graph)
    assert len(orders) == 1
    assert orders[0] == ["CS101", "CS102"]


def test_all_topological_orders_no_deps():
    """Test generating orders with no dependencies"""
    graph = {
        "CS101": set(),
        "CS102": set(),
    }
    
    orders = all_topological_orders(graph)
    assert len(orders) == 2  # Two possible orderings


def test_generate_graduation_paths_student_not_found(mock_client):
    """Test when student is not found"""
    mock_client({
        "student_degree": [],
    })
    
    result = generate_graduation_paths("S999")
    assert "error" in result
    assert result["error"] == "Student not found"


def test_generate_graduation_paths_all_completed(mock_client):
    """Test when all courses are completed"""
    mock_client({
        "student_degree": [{"degree": "CS"}],
        "degree_requirements": [{"course": "CS101"}],
        "completed_courses": [{"course": "CS101"}],
        "prereqs": {},
    })
    
    result = generate_graduation_paths("S1")
    assert "paths" in result
    assert result["paths"] == [["Already graduated"]]


def test_generate_graduation_paths_with_remaining(mock_client):
    """Test generating paths with remaining courses"""
    mock_client({
        "student_degree": [{"degree": "CS"}],
        "degree_requirements": [
            {"course": "CS101"},
            {"course": "CS102"},
        ],
        "completed_courses": [{"course": "CS101"}],
        "prereqs": {
            "CS102": [{"prereq": "CS101"}],
        },
    })
    
    result = generate_graduation_paths("S1")
    assert "paths" in result
    assert "missing_courses" in result
    assert "CS102" in result["missing_courses"]

