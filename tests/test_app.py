import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health():
    """
    health check : api must be up and neo4j must respond
    """
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "neo4j_ok" in data


def test_direct_prereqs_endpoint_exists():
    """
   test the direct prerequisite endpoint
    """
    response = client.get("/courses/AAS 211/prerequisites?all=false")
    #we only test the endpoint exists  not the graph data
    assert response.status_code == 200


def test_all_prereqs_endpoint_exists():
    """
   test recursive prerequisites endpoint
   """
    response = client.get("/courses/AAS 211/prerequisites?all=true")
    assert response.status_code == 200
    assert "prerequisites" in response.json()


def test_cycle_detection_endpoint():
    """
    test cycle detection endpoint
    """
    response = client.get("/courses/cycles")
    assert response.status_code == 200
    assert "cycles" in response.json()


def test_validation_api():
    """
    test prerequisite validation api
    """
    payload = {
        "target_course": "AAS 211",
        "completed_courses": ["AAS 100", "AAS 120"]
    }

    response = client.post("/validation/prerequisites", json=payload)
    assert response.status_code == 200

    data = response.json()
    # check that the keys exist
    assert "can_take" in data
    assert "missing_prerequisites" in data
