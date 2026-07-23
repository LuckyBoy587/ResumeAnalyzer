import pytest
from fastapi.testclient import TestClient
from unittest import mock
from api.app import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}

@mock.patch("src.pipeline.resume_parser.parse_resume")
def test_parse_endpoint_with_embedding(mock_parse_resume):
    mock_parse_resume.return_value = {
        "parsed_resume": {
            "personal_details": {"name": "Alice", "email": "alice@example.com"},
            "skills": ["Python", "FastAPI"]
        },
        "embedding_text": "Skills: Python, FastAPI",
        "embedding_metadata": {
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "dimension": 384,
            "status": "success",
            "char_count": 22,
            "error_message": None,
            "generated_at": "2026-07-23T20:25:00Z"
        },
        "embedding": [0.1] * 384
    }

    payload = {
        "url": "https://example.com/sample_resume.pdf",
        "include_embedding": True
    }

    response = client.post("/parse", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "parsed_resume" in data
    assert "embedding_text" in data
    assert "embedding_metadata" in data
    assert "embedding" in data

    assert data["embedding_metadata"]["dimension"] == 384
    assert len(data["embedding"]) == 384

@mock.patch("src.pipeline.resume_parser.parse_resume")
def test_parse_endpoint_invalid_url(mock_parse_resume):
    payload = {
        "url": "invalid_url_without_protocol",
        "include_embedding": True
    }
    response = client.post("/parse", json=payload)
    assert response.status_code == 400
