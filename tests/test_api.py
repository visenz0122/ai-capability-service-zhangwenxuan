from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "status": "healthy"}


def test_text_summary_returns_required_success_envelope():
    response = client.post(
        "/v1/capabilities/run",
        json={
            "capability": "text_summary",
            "input": {
                "text": "FastAPI makes it easy to build production-ready APIs with Python type hints.",
                "max_length": 36,
            },
            "request_id": "demo-001",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is True
    assert body["data"]["result"] == "FastAPI makes it easy to build..."
    assert body["meta"]["request_id"] == "demo-001"
    assert body["meta"]["capability"] == "text_summary"
    assert isinstance(body["meta"]["elapsed_ms"], int)
    assert body["meta"]["elapsed_ms"] >= 0


def test_keyword_extract_returns_second_capability_result():
    response = client.post(
        "/v1/capabilities/run",
        json={
            "capability": "keyword_extract",
            "input": {
                "text": "AI APIs need stable APIs, provider abstraction, logging, testing, and stable errors.",
                "limit": 4,
            },
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is True
    assert body["data"]["result"] == ["apis", "stable", "abstraction", "errors"]
    assert body["meta"]["capability"] == "keyword_extract"
    assert body["meta"]["request_id"]


def test_missing_text_returns_invalid_input_envelope():
    response = client.post(
        "/v1/capabilities/run",
        json={"capability": "text_summary", "input": {"max_length": 40}},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_INPUT"
    assert "text" in body["error"]["message"].lower()
    assert body["error"]["details"]["field"] == "text"
    assert body["meta"]["capability"] == "text_summary"
    assert body["meta"]["request_id"]


def test_unknown_capability_returns_capability_not_found():
    response = client.post(
        "/v1/capabilities/run",
        json={"capability": "does_not_exist", "input": {"text": "hello"}},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is False
    assert body["error"]["code"] == "CAPABILITY_NOT_FOUND"
    assert body["error"]["details"]["capability"] == "does_not_exist"
    assert body["meta"]["capability"] == "does_not_exist"


def test_request_validation_errors_use_assignment_envelope():
    response = client.post("/v1/capabilities/run", json={"input": {"text": "hello"}})

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert body["meta"]["capability"] == ""
    assert body["meta"]["request_id"]
