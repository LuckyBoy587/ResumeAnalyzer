import os
import re
import logging
import fitz  # PyMuPDF
import spacy
from typing import Dict, List, Set, Any, Optional
from spacy.matcher import PhraseMatcher
from src.extractor.extractor import extract_text_from_pdf

logger = logging.getLogger(__name__)

# Lexicographical mapping structures
SKILL_MAP = {
    "spring boot": "Spring Boot",
    "springboot": "Spring Boot",
    "spring": "Spring Boot",
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "java": "Java",
    "firestore": "Firestore",
    "nosql": "NoSQL",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "python": "Python",
    "html": "HTML",
    "css": "CSS",
    "angular": "Angular",
    "vue": "Vue.js",
    "vue.js": "Vue.js",
    "vuejs": "Vue.js",
    "node": "Node.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "express": "Express.js",
    "express.js": "Express.js",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "Keras",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "Scikit-Learn",
    "scikit learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "hibernate": "Hibernate",
    "junit": "JUnit",
    "git": "Git",
    "github": "GitHub",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "gcp": "Google Cloud",
    "google cloud": "Google Cloud",
    "azure": "Azure",
    "jenkins": "Jenkins",
    "maven": "Maven",
    "gradle": "Gradle",
    "webpack": "Webpack",
    "vite": "Vite",
    "mongodb": "MongoDB",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "redis": "Redis",
    "firebase": "Firebase"
}

DOMAIN_MAP = {
    "full-stack": "Full-Stack",
    "fullstack": "Full-Stack",
    "frontend": "Frontend",
    "front-end": "Frontend",
    "backend": "Backend",
    "back-end": "Backend",
    "devops": "DevOps",
    "cloud native": "Cloud Native",
    "cloud-native": "Cloud Native",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "deep learning": "Deep Learning",
    "dl": "Deep Learning",
    "artificial intelligence": "Artificial Intelligence",
    "ai": "Artificial Intelligence",
    "data science": "Data Science",
    "mobile app": "Mobile App Development",
    "android": "Android Development",
    "ios": "iOS Development"
}

COMPETENCY_MAP = {
    "system design": "System Design",
    "object-oriented programming": "OOP",
    "oop": "OOP",
    "rest api": "REST API",
    "rest apis": "REST API",
    "restful api": "REST API",
    "restful apis": "REST API",
    "data structures": "Data Structures",
    "algorithms": "Algorithms",
    "dsa": "Data Structures & Algorithms",
    "microservices": "Microservices",
    "software engineering": "Software Engineering",
    "database management": "Database Management",
    "dbms": "Database Management",
    "unit testing": "Unit Testing",
    "agile": "Agile Methodology",
    "scrum": "Scrum"
}

INSTITUTIONAL_TERMS = {
    "college", "university", "school", "institute", "academy",
    "vidyapeeth", "department", "dept", "board", "secondary",
    "intermediate", "education", "studying", "degree", "diploma"
}

VALID_LOCATION_SUFFIXES = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy",
    "india", "usa", "uk", "united states", "united kingdom", "germany", "france", "canada", "australia", "singapore", "japan",
    "tamil nadu", "karnataka", "maharashtra", "telangana", "andhra pradesh", "delhi", "haryana", "up", "uttar pradesh", "gujarat", "tn", "ka", "mh", "ts", "ap",
    "spain", "london", "barcelona", "madrid", "paris", "berlin", "italy", "rome", "sweden", "stockholm", "netherlands", "amsterdam"
}

# Globals for lazy loading the spaCy model
_nlp = None

def get_nlp_pipeline():
    """
    Lazy loads the en_core_web_sm spaCy model. Downloads it if missing.
    """
    global _nlp
    if _nlp is None:
        try:
            logger.info("Loading spaCy model 'en_core_web_sm'...")
            _nlp = spacy.load("en_core_web_sm")
        except Exception:
            logger.warning("spaCy model 'en_core_web_sm' not found. Downloading...")
            import subprocess
            import sys
            subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
            _nlp = spacy.load("en_core_web_sm")
            logger.info("Successfully downloaded and loaded spaCy model.")
    return _nlp


def match_section_header_fuzzy(header_text: str) -> str:
    """
    Fuzzy checks if a line corresponds to a standard resume section header.
    """
    if not header_text:
        return "UNKNOWN"

    ontology = {
        "EDUCATION": [
            "education", "academic qualification", "academic background", "academics",
            "educational profile", "educational qualification", "studies", "schooling",
            "academic record", "qualifications"
        ],
        "EXPERIENCE": [
            "experience", "work experience", "employment history", "professional experience",
            "internships", "work history", "industrial training", "professional background",
            "career history", "employment", "professional ventures", "work undertakings"
        ],
        "PROJECTS": [
            "projects", "academic undertakings", "academic projects", "key projects",
            "personal projects", "undertakings", "technical projects", "ventures",
            "selected projects", "notable projects", "project work"
        ],
        "SKILLS": [
            "skills", "core competencies", "technical skills", "competencies",
            "key skills", "technologies", "technical expertise", "skills & tools",
            "languages & frameworks", "languages", "frameworks", "expertise",
            "skills and technologies", "technical proficiencies", "proficiencies"
        ],
        "CERTIFICATIONS": [
            "certifications", "licenses", "courses", "achievements", "accomplishments",
            "awards", "extracurricular activities", "publications", "co-curricular activities",
            "patents", "honors", "certificates", "positions of responsibility"
        ],
        "HEADER": [
            "contact", "contact info", "contact details", "personal details", "personal info",
            "address", "links", "socials", "profiles", "email", "phone"
        ]
    }

    clean_header = header_text.lower().strip()
    clean_header = re.sub(r'[^a-z0-9\s&]', '', clean_header)
    clean_header = re.sub(r'\s+', ' ', clean_header).strip()

    if not clean_header:
        return "UNKNOWN"

    for block, synonyms in ontology.items():
        if clean_header in synonyms:
            return block

    for block, synonyms in ontology.items():
        for syn in synonyms:
            if len(syn) > 3:
                if syn in clean_header:
                    return block
                if len(clean_header) >= 4 and clean_header in syn:
                    return block

    best_block = "UNKNOWN"
    best_score = 0.0
    header_words = set(clean_header.split())

    for block, synonyms in ontology.items():
        for syn in synonyms:
            syn_words = set(syn.split())
            if not header_words or not syn_words:
                continue
            intersection = header_words.intersection(syn_words)
            union = header_words.union(syn_words)
            score = len(intersection) / len(union)
            if score > best_score:
                best_score = score
                best_block = block

    if best_score >= 0.4:
        return best_block

    return "UNKNOWN"


def _is_institutional_context(doc, start: int, end: int) -> bool:
    """
    Excludes institutional keywords/contexts to avoid misidentifying skills.
    """
    for ent in doc.ents:
        if max(start, ent.start) < min(end, ent.end):
            ent_lower = ent.text.lower()
            if any(term in ent_lower for term in ["college", "university", "school", "institute", "academy", "vidyapeeth"]):
                return True

    before_tokens = []
    if start > 0:
        before_tokens.append(doc[start - 1].text.lower())
    if start > 1:
        before_tokens.append(doc[start - 2].text.lower())

    after_tokens = []
    if end < len(doc):
        after_tokens.append(doc[end].text.lower())
    if end < len(doc) - 1:
        after_tokens.append(doc[end + 1].text.lower())

    if len(before_tokens) >= 2 and before_tokens[0] == "of" and before_tokens[1] in INSTITUTIONAL_TERMS:
        return True
    if len(before_tokens) >= 1 and before_tokens[0] in INSTITUTIONAL_TERMS:
        return True

    if len(after_tokens) >= 1 and after_tokens[0] in INSTITUTIONAL_TERMS:
        return True

    return False


def extract_links_from_pdf(local_path: str) -> List[str]:
    """
    Extracts hyperlinked URIs from the PDF pages directly.
    """
    links = []
    try:
        if os.path.exists(local_path):
            with fitz.open(local_path) as doc:
                for page in doc:
                    for link in page.get_links():
                        if link.get('kind') == 2 and 'uri' in link:
                            links.append(link['uri'])
    except Exception as e:
        logger.warning(f"Could not extract links from PDF: {e}")
    return links


def extract_name(doc, clean_text: str) -> Optional[str]:
    """
    Heuristically extracts the candidate's name.
    """
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    if not lines:
        return None
    first_line = lines[0]
    first_line_clean = re.sub(r'[^a-zA-Z\s]', '', first_line).strip()
    words = first_line_clean.split()
    if 1 <= len(words) <= 4 and all(w[0].isupper() for w in words if w.isalpha()):
        return first_line_clean
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            if ent.start_char < 150:
                name_candidate = re.sub(r'[^a-zA-Z\s]', '', ent.text).strip()
                if name_candidate:
                    return name_candidate
    return None


def extract_email(text: str) -> Optional[str]:
    """
    Regex search for email.
    """
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, text)
    if match:
        return match.group(0)
    return None


def extract_phone(text: str) -> Optional[str]:
    """
    Regex search for phone numbers.
    """
    phone_pattern = r'(?:\+?\d{1,3}[\s.-]?)?\(?\d{3,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{4}|(?:\+91-?)?\b\d{10}\b'
    matches = re.findall(phone_pattern, text)
    for m in matches:
        digits = re.sub(r'\D', '', m)
        if 10 <= len(digits) <= 12:
            return m.strip()
    return None


def extract_social_link(links: List[str], text: str, domain: str, pattern: str) -> Optional[str]:
    """
    Matches social media/GitHub/LinkedIn profiles from extracted links or regex search.
    """
    for link in links:
        if domain in link.lower():
            if link.startswith("mailto:"):
                link = link[7:]
            return link
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(0)
    return None


def split_resume_into_sections(clean_text: str) -> Dict[str, List[str]]:
    """
    Segments the resume text into dictionary lists corresponding to headers.
    """
    sections = {
        "HEADER": [],
        "EDUCATION": [],
        "EXPERIENCE": [],
        "PROJECTS": [],
        "SKILLS": [],
        "CERTIFICATIONS": []
    }
    current_section = "HEADER"
    lines = clean_text.split('\n')
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
        if len(line_strip) < 40:
            matched_block = match_section_header_fuzzy(line_strip)
            if matched_block != "UNKNOWN":
                current_section = matched_block
                continue
        sections[current_section].append(line_strip)
    return sections


def extract_projects_structured(project_lines: List[str]) -> List[Dict[str, Any]]:
    """
    Parses and structures project entries from text lines.
    """
    projects_list = []
    current_project = None
    for line in project_lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        is_new_project = False
        title = ""
        techs = []
        if line_clean.startswith("* ") or line_clean.startswith("- ") or line_clean.startswith("• "):
            content = re.sub(r'^[\*\-\•\s]+', '', line_clean).strip()
            if " - " in content:
                is_new_project = True
                parts = content.split(" - ", 1)
                title = parts[0].strip()
                tech_str = parts[1].strip()
                techs = [t.strip() for t in re.split(r',|\s|&', tech_str) if t.strip()]
            else:
                if len(content) < 50:
                    is_new_project = True
                    title = content
        elif " - " in line_clean and len(line_clean) < 100:
            is_new_project = True
            parts = line_clean.split(" - ", 1)
            title = parts[0].strip()
            tech_str = parts[1].strip()
            techs = [t.strip() for t in re.split(r',|\s|&', tech_str) if t.strip()]

        if is_new_project:
            if current_project:
                projects_list.append(current_project)
            current_project = {
                "title": title,
                "description": "",
                "technologies": []
            }
            for t in techs:
                t_lower = t.lower().strip()
                if t_lower in SKILL_MAP:
                    current_project["technologies"].append(SKILL_MAP[t_lower])
                elif t_lower in ["jdbc", "sql", "mysql", "mongodb", "react", "spring"]:
                    current_project["technologies"].append(t.strip())
        else:
            if current_project:
                clean_desc = re.sub(r'^[➢➢\-\*\•\s\u27a2]+', '', line_clean).strip()
                if current_project["description"]:
                    current_project["description"] += " " + clean_desc
                else:
                    current_project["description"] = clean_desc
                for sk_key, sk_val in SKILL_MAP.items():
                    if re.search(r'\b' + re.escape(sk_key) + r'\b', clean_desc.lower()):
                        if sk_val not in current_project["technologies"]:
                            current_project["technologies"].append(sk_val)
                            
    if current_project:
        projects_list.append(current_project)
    for p in projects_list:
        p["technologies"] = sorted(list(set(p["technologies"])))
    return projects_list


def is_bullet_line(line: str) -> bool:
    """
    Checks if a line begins with a bullet character.
    """
    line_clean = line.strip()
    if not line_clean:
        return False
    bullets = ["◦", "\u25e6", "➢", "•", "▪", "", "●", "\u25cf", "▪", "\u25aa", "", "\uf0a7", "*", "-"]
    if any(line_clean.startswith(b) for b in bullets):
        return True
    return False


def is_probable_header(line: str) -> bool:
    """
    Detects if a line looks like a header (contains a date, location, role name, etc.).
    """
    line_clean = line.strip()
    if not line_clean:
        return False

    date_pattern = r"(\d{2}/\d{4}|\bPresent\b|\bSummer\b|\bWinter\b|\bSpring\b|\bFall\b|\bJan\b|\bFeb\b|\bMar\b|\bApr\b|\bMay\b|\bJun\b|\bJul\b|\bAug\b|\bSep\b|\bOct\b|\bNov\b|\bDec\b|\bJanuary\b|\bFebruary\b|\bMarch\b|\bApril\b|\bJune\b|\bJuly\b|\bAugust\b|\bSeptember\b|\bOctober\b|\bNovember\b|\bDecember\b)"
    if re.search(date_pattern, line_clean, re.IGNORECASE):
        return True

    clean_line = re.sub(r"^[◦\u25e6➢•▪\*活跃\-\s]+", "", line_clean).strip()
    words = clean_line.split()
    if not words:
        return False

    is_capitalized = words[0][0].isupper() or words[0][0].isdigit()

    if "," in clean_line:
        parts = clean_line.split(",")
        suffix = parts[-1].strip().lower().replace(".", "")
        if suffix in VALID_LOCATION_SUFFIXES:
            return True

    role_kws = ["engineer", "developer", "assistant", "analyst", "associate", "scientist", "manager", "lead", "specialist", "intern", "internship", "role", "student", "lecturer", "instructor", "member", "writer", "administrator", "consultant"]
    if len(words) <= 5 and is_capitalized:
        if any(re.search(r"\b" + re.escape(kw) + r"\b", clean_line.lower()) for kw in role_kws):
            return True

    if len(words) <= 4 and is_capitalized:
        if not clean_line.endswith(".") and not clean_line.endswith(";"):
            return True

    return False


def clean_description_line(line: str) -> str:
    """
    Removes list indicators and bullet formatting from a description line.
    """
    line_clean = line.strip()
    if line_clean.startswith("◦") or line_clean.startswith("\u25e6") or line_clean.startswith("➢") or line_clean.startswith("•") or line_clean.startswith("▪") or line_clean.startswith("") or line_clean.startswith("*") or line_clean.startswith("-"):
        return re.sub(r"^[◦\u25e6➢•▪\*活跃\-\s]+", "", line_clean).strip()
    return line_clean


def extract_internships_structured(experience_lines: List[str]) -> List[Dict[str, Any]]:
    """
    Structures internship and employment history.
    """
    blocks = []
    current_block_lines = []
    has_seen_bullet_in_current_block = False

    for line in experience_lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        is_bullet = is_bullet_line(line_clean)
        is_header = is_probable_header(line_clean) and not is_bullet

        should_split = False
        if is_header:
            if has_seen_bullet_in_current_block:
                should_split = True
            elif current_block_lines:
                date_pattern = r"(\d{2}/\d{4}|\bPresent\b|\bSummer\b|\bWinter\b|\bSpring\b|\bFall\b|\bJan\b|\bFeb\b|\bMar\b|\bApr\b|\bMay\b|\bJun\b|\bJul\b|\bAug\b|\bSep\b|\bOct\b|\bNov\b|\bDec\b|\bJanuary\b|\bFebruary\b|\bMarch\b|\bApril\b|\bJune\b|\bJuly\b|\bAugust\b|\bSeptember\b|\bOctober\b|\bNovember\b|\bDecember\b)"
                new_has_date = bool(re.search(date_pattern, line_clean, re.IGNORECASE))
                current_has_date = any(re.search(date_pattern, l, re.IGNORECASE) for l in current_block_lines)

                role_kws = ["engineer", "developer", "assistant", "analyst", "associate", "scientist", "manager", "lead", "specialist", "intern", "internship", "role", "student", "lecturer", "instructor", "member", "writer", "administrator", "consultant"]
                new_clean = re.sub(r"^[◦\u25e6➢•▪\*活跃\-\s]+", "", line_clean).strip()
                new_has_role = any(re.search(r"\b" + re.escape(kw) + r"\b", new_clean.lower()) for kw in role_kws)

                current_has_role = False
                for l in current_block_lines:
                    l_clean = re.sub(r"^[◦\u25e6➢•▪\*活跃\-\s]+", "", l).strip()
                    if any(re.search(r"\b" + re.escape(kw) + r"\b", l_clean.lower()) for kw in role_kws):
                        current_has_role = True
                        break

                if (new_has_date and current_has_date) or (new_has_role and current_has_role):
                    should_split = True

        if should_split:
            blocks.append(current_block_lines)
            current_block_lines = []
            has_seen_bullet_in_current_block = False

        if is_bullet:
            has_seen_bullet_in_current_block = True

        current_block_lines.append(line_clean)

    if current_block_lines:
        blocks.append(current_block_lines)

    internships_list = []
    for blk in blocks:
        first_bullet_idx = -1
        for idx, line in enumerate(blk):
            if is_bullet_line(line):
                first_bullet_idx = idx
                break

        if first_bullet_idx != -1:
            header_lines = blk[:first_bullet_idx]
            description_lines = blk[first_bullet_idx:]
        else:
            header_lines = []
            description_lines = []
            for line in blk:
                if is_probable_header(line):
                    header_lines.append(line)
                else:
                    description_lines.append(line)

        if not header_lines:
            continue

        duration = ""
        role = ""
        location = ""
        company = ""

        # A. Find duration
        date_pattern = r"(\d{2}/\d{4}|\bPresent\b|\bSummer\b|\bWinter\b|\bSpring\b|\bFall\b|\bJan\b|\bFeb\b|\bMar\b|\bApr\b|\bMay\b|\bJun\b|\bJul\b|\bAug\b|\bSep\b|\bOct\b|\bNov\b|\bDec\b|\bJanuary\b|\bFebruary\b|\bMarch\b|\bApril\b|\bJune\b|\bJuly\b|\bAugust\b|\bSeptember\b|\bOctober\b|\bNovember\b|\bDecember\b)"
        duration_idx = -1
        for idx, line in enumerate(header_lines):
            if re.search(date_pattern, line, re.IGNORECASE):
                duration_idx = idx
                duration = line
                break
        if duration_idx != -1:
            header_lines.pop(duration_idx)

        # B. Find role
        role_kws = ["engineer", "developer", "assistant", "analyst", "associate", "scientist", "manager", "lead", "specialist", "intern", "internship", "role", "student", "lecturer", "instructor", "member", "writer", "administrator", "consultant"]
        role_idx = -1
        for idx, line in enumerate(header_lines):
            clean_line = re.sub(r"^[◦\u25e6➢•▪\*活跃\-\s]+", "", line).strip()
            if any(re.search(r"\b" + re.escape(kw) + r"\b", clean_line.lower()) for kw in role_kws):
                role_idx = idx
                role = clean_line
                break
        if role_idx != -1:
            header_lines.pop(role_idx)

        # C. Find location and company from remaining lines
        if len(header_lines) >= 2:
            loc_idx = -1
            for idx, line in enumerate(header_lines):
                clean_line = re.sub(r"^[◦\u25e6➢•▪\*活跃\-\s]+", "", line).strip()
                if "," in clean_line:
                    parts = clean_line.split(",")
                    suffix = parts[-1].strip().lower().replace(".", "")
                    if suffix in VALID_LOCATION_SUFFIXES:
                        loc_idx = idx
                        location = clean_line
                        break
            if loc_idx != -1:
                header_lines.pop(loc_idx)

        # D. The remaining first line is the company
        if header_lines:
            company = header_lines[0]

        company = re.sub(r"^[◦\u25e6➢•▪\*活跃\-\s]+", "", company).strip()
        role = re.sub(r"^[◦\u25e6➢•▪\*活跃\-\s]+", "", role).strip()

        # Split company/location if they are combined in location
        if location and "," in location:
            parts = [p.strip() for p in location.split(",")]
            if parts and len(parts[0].split()) <= 4:
                pos_company = parts[0]
                pos_location = ", ".join(parts[1:])
                is_desc = False
                if company:
                    comp_lower = company.lower()
                    if len(company.split()) > 4 and any(w in comp_lower for w in ["startup", "recruitment", "branding", "company", "saas", "technology", "services", "solutions"]):
                        is_desc = True
                    if company.startswith("___") or company.startswith("---") or company.startswith("..."):
                        is_desc = True
                if not company or is_desc:
                    company = pos_company
                    location = pos_location

        # Split role/company/location if they are combined in role
        if role and "," in role:
            parts = [p.strip() for p in role.split(",")]
            if len(parts) >= 2:
                pos_role = parts[0]
                pos_company = parts[1]
                pos_location = ", ".join(parts[2:]) if len(parts) > 2 else ""
                if not company or company.startswith("___"):
                    company = pos_company
                if not location:
                    location = pos_location
                role = pos_role

        if location and duration:
            duration = f"{duration}, {location}"
        elif location:
            duration = location

        cleaned_desc_parts = []
        for l in description_lines:
            l_clean = clean_description_line(l)
            if l_clean and not re.match(r'^[\s_=\-\*\•\u25cf\u25e6\u2022]+$', l_clean):
                cleaned_desc_parts.append(l_clean)

        internships_list.append({
            "company": company or None,
            "role": role or None,
            "duration": duration or None,
            "description": " ".join(cleaned_desc_parts) or None
        })

    return internships_list


def extract_cgpa(text: str, education_text: Optional[str] = None) -> Optional[float]:
    """
    Parses CGPA/GPA or Percentage values from the text.
    """
    search_text = education_text if education_text else text

    pattern1 = r"\b(?:cgpa|gpa|g\.p\.a|c\.g\.p\.a)[:\-\s]*(\d{1,2}(?:\.\d{1,2})?)"
    pattern2 = r"(\d{1,2}\.\d{1,2})\s*(?:/10|cgpa|gpa)"

    match1 = re.search(pattern1, search_text, re.IGNORECASE)
    if match1:
        try:
            val = float(match1.group(1))
            if val <= 10.0 or val <= 100.0:
                return val
        except ValueError:
            pass

    match2 = re.search(pattern2, search_text, re.IGNORECASE)
    if match2:
        try:
            val = float(match2.group(1))
            if val <= 10.0:
                return val
        except ValueError:
            pass

    pct_match = re.search(r"(\d{2}(?:\.\d{1,2})?)\s*%", search_text)
    if pct_match:
        try:
            return float(pct_match.group(1))
        except ValueError:
            pass

    if education_text and search_text != text:
        match1 = re.search(pattern1, text, re.IGNORECASE)
        if match1:
            try:
                val = float(match1.group(1))
                if val <= 10.0 or val <= 100.0:
                    return val
            except ValueError:
                pass
        match2 = re.search(pattern2, text, re.IGNORECASE)
        if match2:
            try:
                val = float(match2.group(1))
                if val <= 10.0:
                    return val
            except ValueError:
                pass

    return None


def classify_experience_level(internships_count: int, projects_count: int, skills_count: int) -> str:
    """
    Determines candidate level based on counts of internships, projects, and skills.
    """
    if internships_count >= 2:
        return "Advanced"
    elif internships_count == 1 or projects_count >= 2:
        return "Intermediate"
    else:
        return "Beginner"


def parse_college_resume_intelligent(local_path: str, clean_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entity parsing engine using spaCy PhraseMatcher and custom heuristics.
    """
    if clean_text is None:
        clean_text = extract_text_from_pdf(local_path)

    nlp = get_nlp_pipeline()
    doc = nlp(clean_text)

    # 1. Segment structural sections
    sections = split_resume_into_sections(clean_text)

    # 2. Extract Personal Details & links
    links = extract_links_from_pdf(local_path)
    name = extract_name(doc, clean_text)
    email = extract_email(clean_text)
    phone = extract_phone(clean_text)

    if not email:
        for link in links:
            if link.startswith("mailto:"):
                email = link[7:]
                break

    github = extract_social_link(links, clean_text, "github.com", r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+")
    linkedin = extract_social_link(links, clean_text, "linkedin.com", r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|pub)/[a-zA-Z0-9_-]+")

    personal_details = {
        "name": name,
        "email": email,
        "phone": phone,
        "github": github,
        "linkedin": linkedin
    }

    # 3. Parse Technical Entities via matcher
    skills = set()
    domains = set()
    competencies = set()

    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

    for sk in SKILL_MAP.keys():
        matcher.add("SKILL", [nlp.make_doc(sk)])
    for dk in DOMAIN_MAP.keys():
        matcher.add("DOMAIN", [nlp.make_doc(dk)])
    for ck in COMPETENCY_MAP.keys():
        matcher.add("COMPETENCY", [nlp.make_doc(ck)])

    matches = matcher(doc)

    for match_id, start, end in matches:
        label = nlp.vocab.strings[match_id]
        matched_str = doc[start:end].text.lower()

        if _is_institutional_context(doc, start, end):
            continue

        if label == "SKILL":
            norm = SKILL_MAP.get(matched_str)
            if norm:
                skills.add(norm)
        elif label == "DOMAIN":
            norm = DOMAIN_MAP.get(matched_str)
            if norm:
                domains.add(norm)
        elif label == "COMPETENCY":
            norm = COMPETENCY_MAP.get(matched_str)
            if norm:
                competencies.add(norm)

    for ent in doc.ents:
        if ent.label_ in ["ORG", "PRODUCT"]:
            ent_clean = ent.text.lower().strip()
            if ent_clean in SKILL_MAP:
                if not _is_institutional_context(doc, ent.start, ent.end):
                    skills.add(SKILL_MAP[ent_clean])
            elif ent_clean in DOMAIN_MAP:
                if not _is_institutional_context(doc, ent.start, ent.end):
                    domains.add(DOMAIN_MAP[ent_clean])
            elif ent_clean in COMPETENCY_MAP:
                if not _is_institutional_context(doc, ent.start, ent.end):
                    competencies.add(COMPETENCY_MAP[ent_clean])

    skills_list = sorted(list(skills))
    domains_list = sorted(list(domains))
    competencies_list = sorted(list(competencies))

    # 4. Extract Projects, Internships, Certifications, and CGPA
    projects_list = extract_projects_structured(sections["PROJECTS"])
    internships_list = extract_internships_structured(sections["EXPERIENCE"])

    certifications_list = []
    current_cert = ""
    for line in sections["CERTIFICATIONS"]:
        line_clean = line.strip()
        if not line_clean:
            continue
        if line_clean.startswith("* ") or line_clean.startswith("- ") or line_clean.startswith("• ") or line_clean.startswith("➢ "):
            if current_cert:
                certifications_list.append(current_cert)
            current_cert = re.sub(r"^[➢➢\-\*\•\s\u27a2]+", "", line_clean).strip()
        else:
            if current_cert:
                current_cert += " " + line_clean
            else:
                current_cert = line_clean
    if current_cert:
        certifications_list.append(current_cert)

    education_text = "\n".join(sections["EDUCATION"])
    cgpa_val = extract_cgpa(clean_text, education_text)
    experience_level_val = classify_experience_level(len(internships_list), len(projects_list), len(skills_list))

    return {
        "personal_details": personal_details,
        "skills": skills_list,
        "projects": projects_list,
        "domains": domains_list,
        "competencies": competencies_list,
        "certifications": certifications_list,
        "cgpa": cgpa_val,
        "internships": internships_list,
        "experience_level": experience_level_val
    }

def parse_resume_to_entities(local_path: str, clean_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Entrypoint wrapper for parsing.
    """
    return parse_college_resume_intelligent(local_path, clean_text=clean_text)

def detect_file_type(file_path: str) -> str:
    """
    Detects if the file is a PDF, DOCX, or other type by reading its magic bytes.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    with open(file_path, "rb") as f:
        header = f.read(4)
        
    if header.startswith(b"%PDF"):
        return "pdf"
    elif header.startswith(b"PK\x03\x04"):
        return "docx"
    else:
        # Check by extension if magic bytes are ambiguous
        _, ext = os.path.splitext(file_path.lower())
        if ext == ".pdf":
            return "pdf"
        elif ext in [".docx", ".doc"]:
            return "docx"
        return "unknown"
