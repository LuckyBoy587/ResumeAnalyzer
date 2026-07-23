import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def build_embedding_text(parsed_data: Dict[str, Any], clean_text: str = "") -> str:
    """
    Constructs a section-weighted canonical string representation from parsed resume data.
    
    CRITICAL CONSTRAINT: Explicitly excludes candidate name, email, phone, linkedin, github,
    and CGPA to prevent PII exposure and focus dense vectors purely on technical capabilities.

    Args:
        parsed_data (dict): The structured dictionary returned by resume parser.
        clean_text (str): Optional raw clean text extracted from PDF as fallback context.

    Returns:
        str: Formatted text string optimized for sentence-transformers embedding generation.
    """
    parts: List[str] = []

    # 1. Experience Level
    exp_level = parsed_data.get("experience_level")
    if exp_level:
        parts.append(f"Experience Level: {exp_level}")

    # 2. Technical Skills
    skills = parsed_data.get("skills") or []
    if skills:
        skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
        parts.append(f"Skills: {skills_str}")

    # 3. Domains
    domains = parsed_data.get("domains") or []
    if domains:
        domains_str = ", ".join(domains) if isinstance(domains, list) else str(domains)
        parts.append(f"Domains: {domains_str}")

    # 4. Competencies
    competencies = parsed_data.get("competencies") or []
    if competencies:
        competencies_str = ", ".join(competencies) if isinstance(competencies, list) else str(competencies)
        parts.append(f"Competencies: {competencies_str}")

    # 5. Internships / Employment Experience
    internships = parsed_data.get("internships") or []
    if isinstance(internships, list) and internships:
        exp_parts = []
        for item in internships:
            if not isinstance(item, dict):
                continue
            role = item.get("role") or ""
            company = item.get("company") or ""
            desc = item.get("description") or ""
            
            entry = ""
            if role and company:
                entry = f"{role} at {company}"
            elif role:
                entry = role
            elif company:
                entry = company
                
            if desc:
                entry = f"{entry}: {desc}" if entry else desc
                
            if entry.strip():
                exp_parts.append(entry.strip())
        if exp_parts:
            parts.append(f"Experience: {' | '.join(exp_parts)}")

    # 6. Projects
    projects = parsed_data.get("projects") or []
    if isinstance(projects, list) and projects:
        proj_parts = []
        for proj in projects:
            if not isinstance(proj, dict):
                continue
            title = proj.get("title") or ""
            desc = proj.get("description") or ""
            techs = proj.get("technologies") or []
            tech_str = ", ".join(techs) if isinstance(techs, list) else str(techs)
            
            p_entry = title
            if desc:
                p_entry = f"{p_entry}: {desc}" if p_entry else desc
            if tech_str:
                p_entry = f"{p_entry} (Tech: {tech_str})"
                
            if p_entry.strip():
                proj_parts.append(p_entry.strip())
        if proj_parts:
            parts.append(f"Projects: {' | '.join(proj_parts)}")

    # 7. Certifications
    certs = parsed_data.get("certifications") or []
    if certs:
        certs_str = ", ".join(certs) if isinstance(certs, list) else str(certs)
        parts.append(f"Certifications: {certs_str}")

    embedding_text = " | ".join(parts).strip()

    # Fallback to clean_text if structured details yielded very minimal text
    if len(embedding_text) < 30 and clean_text.strip():
        logger.info("Structured entities provided insufficient text. Incorporating clean_text fallback.")
        # Strip common email and phone patterns from fallback clean_text
        sanitized_raw = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', clean_text)
        sanitized_raw = re.sub(r'(?:\+?\d{1,3}[\s.-]?)?\(?\d{3,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{4}', '', sanitized_raw)
        sanitized_raw = re.sub(r'\s+', ' ', sanitized_raw).strip()
        
        if embedding_text:
            embedding_text = f"{embedding_text} | Summary: {sanitized_raw[:500]}"
        else:
            embedding_text = f"Summary: {sanitized_raw[:500]}"

    return embedding_text
