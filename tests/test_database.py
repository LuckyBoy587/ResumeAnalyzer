import pytest
from unittest import mock
from src.database.db import get_normalized_db_url, init_db, save_resume_to_db

@mock.patch("src.database.db.DATABASE_URL", "postgres://user:pass@host:5432/db")
def test_get_normalized_db_url_postgres():
    url = get_normalized_db_url()
    assert url == "postgresql://user:pass@host:5432/db"

@mock.patch("src.database.db.DATABASE_URL", "postgresql://user:pass@host:5432/db")
def test_get_normalized_db_url_postgresql():
    url = get_normalized_db_url()
    assert url == "postgresql://user:pass@host:5432/db"

@mock.patch("src.database.db.get_db_connection")
def test_init_db(mock_get_conn):
    mock_conn = mock.MagicMock()
    mock_cur = mock.MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    init_db()

    mock_get_conn.assert_called_once()
    mock_cur.execute.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()

@mock.patch("src.database.db.get_db_connection")
def test_save_resume_to_db(mock_get_conn):
    mock_conn = mock.MagicMock()
    mock_cur = mock.MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    
    # Mock RETURNING id
    mock_cur.fetchone.return_value = ("550e8400-e29b-41d4-a716-446655440000",)

    parsed_data = {
        "personal_details": {
            "name": "Test Candidate",
            "email": "test@example.com",
            "phone": "123456",
            "github": "http://github.com",
            "linkedin": "http://linkedin.com"
        },
        "skills": ["Python", "Docker"],
        "domains": ["Backend"],
        "competencies": ["OOP"],
        "experience_level": "Senior",
        "cgpa": 3.8
    }

    result = save_resume_to_db(parsed_data)

    assert result == {"id": "550e8400-e29b-41d4-a716-446655440000", "status": "persisted"}
    mock_cur.execute.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()
