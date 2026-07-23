import pytest
from src.embedding.embedding_builder import build_embedding_text

def test_build_embedding_text_excludes_pii_and_cgpa():
    parsed_data = {
        "personal_details": {
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "phone": "+1-123-456-7890",
            "github": "https://github.com/janesmith",
            "linkedin": "https://linkedin.com/in/janesmith"
        },
        "skills": ["Python", "FastAPI", "Docker"],
        "domains": ["Backend", "Microservices"],
        "competencies": ["System Design", "REST API"],
        "projects": [
            {
                "title": "Resume Microservice",
                "description": "Engineered a high throughput resume parser.",
                "technologies": ["Python", "FastAPI"]
            }
        ],
        "internships": [
            {
                "company": "TechCorp",
                "role": "Software Engineer Intern",
                "description": "Developed cloud services."
            }
        ],
        "certifications": ["AWS Solutions Architect"],
        "cgpa": 3.92,
        "experience_level": "Intermediate"
    }

    text = build_embedding_text(parsed_data)

    # Assert PII is NOT in text
    assert "Jane Smith" not in text
    assert "jane.smith@example.com" not in text
    assert "+1-123-456-7890" not in text
    assert "github.com" not in text
    assert "linkedin.com" not in text

    # Assert CGPA is NOT in text
    assert "3.92" not in text
    assert "CGPA" not in text

    # Assert technical sections are included
    assert "Experience Level: Intermediate" in text
    assert "Skills: Python, FastAPI, Docker" in text
    assert "Domains: Backend, Microservices" in text
    assert "Competencies: System Design, REST API" in text
    assert "Resume Microservice" in text
    assert "TechCorp" in text
    assert "AWS Solutions Architect" in text


def test_build_embedding_text_empty_data():
    parsed_data = {
        "personal_details": {},
        "skills": [],
        "domains": [],
        "competencies": [],
        "projects": [],
        "internships": [],
        "certifications": [],
        "cgpa": None,
        "experience_level": "Beginner"
    }

    text = build_embedding_text(parsed_data, clean_text="Raw fallback resume text content.")
    assert "Experience Level: Beginner" in text
    assert "Summary: Raw fallback resume text content." in text
