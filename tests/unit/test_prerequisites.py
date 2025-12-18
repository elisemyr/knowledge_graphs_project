import pytest
from backend.services import prerequisites


class MockNeo4jClient:
    def __init__(self, results):
        self._results = results

    def query(self, query, params=None, read_only=True):
        return self._results


@pytest.fixture
def mock_client(monkeypatch):
    def _mock(results):
        monkeypatch.setattr(
            prerequisites,
            "get_neo4j_client",
            lambda: MockNeo4jClient(results),
        )
    return _mock


def test_get_direct_prerequisites_basic(mock_client):
    mock_client([
        {"code": "MATH101"},
        {"code": "CS100"},
    ])

    result = prerequisites.get_direct_prerequisites("CS200")
    assert sorted(result) == ["CS100", "MATH101"]


def test_get_direct_prerequisites_empty(mock_client):
    mock_client([])

    result = prerequisites.get_direct_prerequisites("INTRO101")
    assert result == []

def test_check_student_can_take_course_not_found(mock_client):
    # Neo4j returns no rows → course not found
    mock_client([])

    result = prerequisites.check_student_can_take("S1", "CS999")

    assert result["can_take"] is False
    assert result["reason"] == "course_not_found"
    assert result["required"] == []
    assert result["completed"] == []


def test_check_student_can_take_student_not_found(mock_client):
    # Course exists, student does not
    mock_client([{
        "course": "CS200",
        "required": ["CS100"],
        "completed": [],
        "student_exists": False,
    }])

    result = prerequisites.check_student_can_take("S404", "CS200")

    assert result["can_take"] is False
    assert result["reason"] == "student_not_found"
    assert result["missing"] == ["CS100"]


def test_check_student_can_take_ok(mock_client):
    # Student completed all prerequisites
    mock_client([{
        "course": "CS200",
        "required": ["CS100"],
        "completed": ["CS100"],
        "student_exists": True,
    }])

    result = prerequisites.check_student_can_take("S1", "CS200")

    assert result["can_take"] is True
    assert result["missing"] == []
    assert result["reason"] == "ok"


def test_check_student_can_take_missing_prereq(mock_client):
    # Student missing prerequisites
    mock_client([{
        "course": "CS200",
        "required": ["CS100", "MATH101"],
        "completed": ["CS100"],
        "student_exists": True,
    }])

    result = prerequisites.check_student_can_take("S1", "CS200")

    assert result["can_take"] is False
    assert result["missing"] == ["MATH101"]
    assert result["reason"] == "missing_prerequisites"

