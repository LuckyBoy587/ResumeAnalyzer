import pytest
from src.parser.parser import (
    match_section_header_fuzzy,
    extract_email,
    extract_phone,
    extract_cgpa,
    classify_experience_level,
    extract_projects_structured,
    extract_internships_structured,
)

def test_match_section_header_fuzzy():
    assert match_section_header_fuzzy("Academic Qualification") == "EDUCATION"
    assert match_section_header_fuzzy("Employment History") == "EXPERIENCE"
    assert match_section_header_fuzzy("Work Experience") == "EXPERIENCE"
    assert match_section_header_fuzzy("Key Projects") == "PROJECTS"
    assert match_section_header_fuzzy("Technical Experience") == "PROJECTS"
    assert match_section_header_fuzzy("Core Competencies") == "SKILLS"
    assert match_section_header_fuzzy("Licenses & Certifications") == "CERTIFICATIONS"
    assert match_section_header_fuzzy("Contact Info") == "HEADER"
    assert match_section_header_fuzzy("Random Title Here") == "UNKNOWN"

def test_extract_email():
    assert extract_email("My email is kowshik@example.com.") == "kowshik@example.com"
    assert extract_email("Contact: test.user+label@g.domain.co.in") == "test.user+label@g.domain.co.in"
    assert extract_email("No email here.") is None

def test_extract_phone():
    assert extract_phone("My number is +91-9876543210.") == "+91-9876543210"
    assert extract_phone("Call me at 9876543210") == "9876543210"
    assert extract_phone("Office: (123) 456-7890") == "(123) 456-7890"
    assert extract_phone("Invalid 12345") is None

def test_extract_cgpa():
    assert extract_cgpa("I got a CGPA of 9.2 in college.") == 9.2
    assert extract_cgpa("GPA: 3.8/10") == 3.8
    assert extract_cgpa("Percentage: 85.5% in high school.") == 85.5
    assert extract_cgpa("No grades mentioned.") is None
    # Test with education context search
    assert extract_cgpa("Full text: 9.8 CGPA", "education: CGPA of 8.5") == 8.5

def test_classify_experience_level():
    assert classify_experience_level(2, 0, 10) == "Advanced"
    assert classify_experience_level(1, 2, 5) == "Intermediate"
    assert classify_experience_level(0, 1, 3) == "Beginner"

def test_extract_projects_structured():
    project_lines = [
        "Project 1 - Python, React",
        "* Developed a resume extractor using spaCy",
        "Project 2 - Spring Boot, SQL",
        "- Built enterprise endpoints for billing system",
    ]
    projects = extract_projects_structured(project_lines)
    assert len(projects) == 2
    assert projects[0]["title"] == "Project 1"
    assert "Python" in projects[0]["technologies"]
    assert "React" in projects[0]["technologies"]
    assert "resume extractor" in projects[0]["description"]
    
    assert projects[1]["title"] == "Project 2"
    assert "Spring Boot" in projects[1]["technologies"]

def test_extract_internships_structured():
    experience_lines = [
        "Software Engineer Intern",
        "Google, Mountain View, CA",
        "May 2024 - Aug 2024",
        "• Worked on Gemini models and agent workflows.",
        "• Collaborated with product team.",
    ]
    internships = extract_internships_structured(experience_lines)
    assert len(internships) == 1
    assert internships[0]["company"] == "Google"
    assert internships[0]["role"] == "Software Engineer Intern"
    assert "May 2024 - Aug 2024" in internships[0]["duration"]
    assert "Worked on Gemini models" in internships[0]["description"]

    # Test combined role and company separated by hyphen
    experience_lines_combined = [
        "HCL - Software Engineering Intern",
        "• Engineered a full-stack image gallery application.",
    ]
    internships_combined = extract_internships_structured(experience_lines_combined)
    assert len(internships_combined) == 1
    assert internships_combined[0]["company"] == "HCL"
    assert internships_combined[0]["role"] == "Software Engineering Intern"

    # Test combined role and company separated by em-dash (—) and en-dash (–)
    experience_lines_em = [
        "HCL - Software Engineering Intern",
        "• Engineered a full-stack image gallery application.",
    ]
    internships_em = extract_internships_structured(experience_lines_em)
    assert len(internships_em) == 1
    assert internships_em[0]["company"] == "HCL"
    assert internships_em[0]["role"] == "Software Engineering Intern"

    experience_lines_en = [
        "HCL – Software Engineering Intern",
        "• Engineered a full-stack image gallery application.",
    ]
    internships_en = extract_internships_structured(experience_lines_en)
    assert len(internships_en) == 1
    assert internships_en[0]["company"] == "HCL"
    assert internships_en[0]["role"] == "Software Engineering Intern"
