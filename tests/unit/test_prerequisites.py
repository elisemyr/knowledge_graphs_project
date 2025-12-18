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


