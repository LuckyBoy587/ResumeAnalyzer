import fitz  # PyMuPDF
import spacy
import os
import re
import requests
import json
from typing import Dict, List, Set, any
from spacy.matcher import PhraseMatcher

# Seed lexicographical token dictionaries for intelligent normalization mapping
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

# Institutional patterns to filter out false positive entities
INSTITUTIONAL_TERMS = {
    "college", "university", "school", "institute", "academy", 
    "vidyapeeth", "department", "dept", "board", "secondary", 
    "intermediate", "education", "studying", "degree", "diploma"
}

# Initialize NLP Pipeline
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    print("spaCy 'en_core_web_sm' pipeline not found. Attempting download...")
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")


def download_file_from_url(url: str, output_path: str = "temp_resume.pdf") -> str:
    """
    Downloads a PDF file from a Google Drive, GitHub, or direct URL,
    and returns the local file path. If the input is a local path, returns it directly.
    """
    if os.path.exists(url):
        return url
        
    if not (url.startswith("http://") or url.startswith("https://")):
        return url

    # Google Drive URL pattern matching
    gd_match = re.search(r'(?:drive\.google\.com/(?:file/d/|open\?id=|uc\\?id=|uc\?export=download&id=)|docs\.google\.com/file/d/)([a-zA-Z0-9_-]+)', url)
    if gd_match:
        file_id = gd_match.group(1)
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        session = requests.Session()
        response = session.get(download_url, stream=True)
        
        confirm_token = None
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                confirm_token = value
                break
                
        if confirm_token:
            download_url += f"&confirm={confirm_token}"
            response = session.get(download_url, stream=True)
            
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return output_path

    # GitHub URL pattern matching (converting web link to raw content link)
    github_match = re.search(r'github\.com/([^/]+)/([^/]+)/(?:blob|raw)/([^/]+)/(.+)', url, re.IGNORECASE)
    if github_match:
        user, repo, branch, path = github_match.groups()
        path = path.split('?')[0].split('#')[0]
        download_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"
    else:
        download_url = url

    # Direct/fallback URL download
    response = requests.get(download_url, stream=True)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return output_path


def extract_text_with_spatial_bounds(pdf_path: str) -> str:
    """
    Extracts raw text from a PDF file using spatial layout analysis to preserve
    multi-column reading flows and text grid alignments.
    """
    is_url = pdf_path.startswith("http://") or pdf_path.startswith("https://")
    local_path = pdf_path
    
    if is_url:
        local_path = download_file_from_url(pdf_path)
        
    try:
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Target document not found at: {local_path}")

        text_parts = []
        with fitz.open(local_path) as doc:
            for page in doc:
                rect = page.rect
                width = rect.width
                mid_x = width / 2
                
                # Get text blocks: (x0, y0, x1, y1, "text", block_no, block_type)
                blocks = page.get_text("blocks")
                text_blocks = [b for b in blocks if b[6] == 0]
                
                # Identify spanning blocks (horizontal dividers across the midline)
                spanning_blocks = []
                for b in text_blocks:
                    x0, y0, x1, y1, _, _, _ = b
                    if x0 < mid_x - 30 and x1 > mid_x + 30:
                        spanning_blocks.append(b)
                
                spanning_blocks.sort(key=lambda x: x[1]) # Sort dividers vertically
                
                # Helper to assign block zones and columns
                def get_block_location(b):
                    x0, y0, x1, y1, _, _, _ = b
                    # Check if spanning block itself
                    for idx, sb in enumerate(spanning_blocks):
                        if b == sb:
                            return (idx * 2 + 1, 0, y0)
                    
                    # Determine zone index (even numbers)
                    zone_idx = 0
                    for idx, sb in enumerate(spanning_blocks):
                        if y0 >= sb[3] - 5: # With a small tolerance
                            zone_idx = (idx + 1) * 2
                            
                    # Column classification
                    if x1 <= mid_x + 15:
                        col = 0
                    elif x0 >= mid_x - 15:
                        col = 1
                    else:
                        col = 2
                    return (zone_idx, col, y0)
                
                # Group text blocks into zone bins
                zone_blocks = {}
                for b in text_blocks:
                    loc = get_block_location(b)
                    z_idx = loc[0]
                    if z_idx not in zone_blocks:
                        zone_blocks[z_idx] = []
                    zone_blocks[z_idx].append(b)
                
                # Sort each zone dynamically based on its structural characteristics
                for z_idx in sorted(zone_blocks.keys()):
                    z_list = zone_blocks[z_idx]
                    if z_idx % 2 == 1:
                        # Spanning zone: single or simple horizontal row. Sort by y0, then x0.
                        z_list.sort(key=lambda x: (x[1], x[0]))
                    else:
                        # Check if zone contains two vertical columns
                        has_two_columns = False
                        lefts = [b for b in z_list if b[2] <= mid_x + 15]
                        rights = [b for b in z_list if b[0] >= mid_x - 15]
                        
                        if lefts and rights:
                            for l in lefts:
                                for r in rights:
                                    overlap = min(l[3], r[3]) - max(l[1], r[1])
                                    h_l = l[3] - l[1]
                                    h_r = r[3] - r[1]
                                    if overlap > 0.3 * min(h_l, h_r):
                                        has_two_columns = True
                                        break
                                if has_two_columns:
                                    break
                                    
                        if has_two_columns:
                            # Sort by column first (Left = 0, Right = 1), then vertically
                            def col_sort_key(b):
                                x0, y0, x1, _, _, _, _ = b
                                col = 0 if x1 <= mid_x + 15 else (1 if x0 >= mid_x - 15 else 2)
                                return (col, y0)
                            z_list.sort(key=col_sort_key)
                        else:
                            # Single-column: sort by y0, then x0
                            z_list.sort(key=lambda x: (x[1], x[0]))
                            
                    for b in z_list:
                        text_parts.append(b[4].strip())
                        
        return "\n".join(text_parts)
    finally:
        if is_url and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception as e:
                print(f"Warning: Could not remove temporary file {local_path}: {e}")


def clean_and_normalize_text(raw_text: str) -> str:
    """
    Cleans raw layout-preserved text: filters layout noise, strips system artifacts,
    and normalizes whitespaces/unicode representations.
    """
    if not raw_text:
        return ""
        
    # Replace unicode variants
    replacements = {
        '\u201c': '"', '\u201d': '"',
        '\u2018': "'", '\u2019': "'",
        '\u2013': '-', '\u2014': '-',
        '\u2022': '*', '\u2027': '*',
        '\u00a0': ' ',
        '\r\n': '\n', '\r': '\n'
    }
    
    cleaned = raw_text
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
        
    # Filter non-printable control characters (keep newline and tabs)
    cleaned = "".join(ch for ch in cleaned if ch.isprintable() or ch in ('\n', '\t'))
    
    # Collapse multiple consecutive horizontal spaces
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    
    # Collapse multiple consecutive newlines (max 2 consecutive newlines)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # Trim leading/trailing spaces from each line
    lines = [line.strip() for line in cleaned.split('\n')]
    cleaned = '\n'.join(lines)
    
    return cleaned.strip()


def match_section_header_fuzzy(header_text: str) -> str:
    """
    Evaluates section header variations and maps them to standard system blocks:
    EDUCATION, EXPERIENCE, PROJECTS, SKILLS, CERTIFICATIONS, or UNKNOWN.
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
        ]
    }
    
    clean_header = header_text.lower().strip()
    clean_header = re.sub(r'[^a-z0-9\s&]', '', clean_header)
    clean_header = re.sub(r'\s+', ' ', clean_header).strip()
    
    if not clean_header:
        return "UNKNOWN"
        
    # 1. Check exact matches in synonyms
    for block, synonyms in ontology.items():
        if clean_header in synonyms:
            return block
            
    # 2. Check substring overlaps
    for block, synonyms in ontology.items():
        for syn in synonyms:
            if len(syn) > 3 and (syn in clean_header or clean_header in syn):
                return block
                
    # 3. Fallback Jaccard word similarity
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
    Internal helper to analyze token contexts and exclude institutional naming structures.
    """
    # 1. Check spaCy named entity tags (ORG / GPE / PERSON) spanning this token window
    for ent in doc.ents:
        if max(start, ent.start) < min(end, ent.end):
            ent_lower = ent.text.lower()
            if any(term in ent_lower for term in ["college", "university", "school", "institute", "academy", "vidyapeeth"]):
                return True
                
    # 2. Check immediately adjacent tokens
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
        
    # Check if a preposition links it to an institutional term (e.g., "university of java")
    if len(before_tokens) >= 2 and before_tokens[0] == "of" and before_tokens[1] in INSTITUTIONAL_TERMS:
        return True
    if len(before_tokens) >= 1 and before_tokens[0] in INSTITUTIONAL_TERMS:
        return True
        
    # Check if followed directly by an institutional term (e.g., "spring college")
    if len(after_tokens) >= 1 and after_tokens[0] in INSTITUTIONAL_TERMS:
        return True
        
    return False


def extract_links_from_pdf(pdf_path: str) -> List[str]:
    """
    Retrieves all target hyperlinked URIs from the PDF pages.
    """
    is_url = pdf_path.startswith("http://") or pdf_path.startswith("https://")
    local_path = pdf_path
    if is_url:
        local_path = download_file_from_url(pdf_path)
    links = []
    try:
        if os.path.exists(local_path):
            with fitz.open(local_path) as doc:
                for page in doc:
                    for link in page.get_links():
                        if link.get('kind') == 2 and 'uri' in link:
                            links.append(link['uri'])
    except Exception as e:
        print(f"Warning: could not extract links: {e}")
    return links


def extract_name(doc, clean_text: str) -> str:
    """
    Heuristically extracts the candidate's name from first line or PERSON entity.
    """
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    if not lines:
        return None
        
    first_line = lines[0]
    first_line_clean = re.sub(r'[^a-zA-Z\s]', '', first_line).strip()
    words = first_line_clean.split()
    
    if 1 <= len(words) <= 4 and all(w[0].isupper() for w in words if w.isalpha()):
        return first_line_clean
        
    # spaCy PERSON check near the beginning
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            if ent.start_char < 150:
                name_candidate = re.sub(r'[^a-zA-Z\s]', '', ent.text).strip()
                if name_candidate:
                    return name_candidate
                    
    if len(first_line_clean) < 40 and len(first_line_clean) > 0:
        return first_line_clean
        
    return None


def extract_email(text: str) -> str:
    """
    Extracts the first valid email address from text.
    """
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, text)
    if match:
        return match.group(0)
    return None


def extract_phone(text: str) -> str:
    """
    Extracts the first valid phone number from text.
    """
    phone_pattern = r'(?:\+?\d{1,3}[\s.-]?)?\(?\d{3,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{4}|(?:\+91-?)?\b\d{10}\b'
    matches = re.findall(phone_pattern, text)
    for m in matches:
        digits = re.sub(r'\D', '', m)
        if 10 <= len(digits) <= 12:
            return m.strip()
    return None


def extract_social_link(links: List[str], text: str, domain: str, pattern: str) -> str:
    """
    Finds social profile links by inspecting PDF hyperlinks and plain text fallback.
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
    Categorizes clean resume text lines into structured section bins.
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


def extract_projects_structured(project_lines: List[str]) -> List[Dict[str, any]]:
    """
    Parses project blocks into strongly typed project schemas.
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
                    
                # Scan description for other matching skills
                for sk_key, sk_val in SKILL_MAP.items():
                    if re.search(r'\b' + re.escape(sk_key) + r'\b', clean_desc.lower()):
                        if sk_val not in current_project["technologies"]:
                            current_project["technologies"].append(sk_val)
                            
    if current_project:
        projects_list.append(current_project)
        
    for p in projects_list:
        p["technologies"] = sorted(list(set(p["technologies"])))
        
    return projects_list


def extract_internships_structured(experience_lines: List[str]) -> List[Dict[str, any]]:
    """
    Parses experience blocks into strongly typed internship models.
    """
    internships_list = []
    current_internship = None
    
    i = 0
    while i < len(experience_lines):
        line = experience_lines[i].strip()
        is_role = any(kw in line.lower() for kw in ["intern", "engineer", "developer", "analyst", "associate", "manager", "lead"])
        
        if is_role and len(line) < 80:
            if current_internship:
                internships_list.append(current_internship)
                
            role = line
            company = ""
            duration = ""
            description_lines = []
            
            if i + 1 < len(experience_lines):
                company = experience_lines[i + 1].strip()
                
            i_offset = 2
            if i + 2 < len(experience_lines):
                date_line = experience_lines[i + 2].strip()
                if re.search(r'(\d{2}/\d{4}|\bPresent\b|\bIncoming\b|\bPresent|\bJan|\bFeb|\bMar|\bApr|\bMay|\bJun|\bJul|\bAug|\bSep|\bOct|\bNov|\bDec)', date_line):
                    duration = date_line
                    i_offset = 3
                    
            j = i + i_offset
            while j < len(experience_lines):
                next_line = experience_lines[j].strip()
                next_is_role = any(kw in next_line.lower() for kw in ["intern", "engineer", "developer", "analyst", "associate"]) and len(next_line) < 80
                if next_is_role:
                    break
                clean_bullet = re.sub(r'^[➢➢\-\*\•\s\u27a2]+', '', next_line).strip()
                if clean_bullet:
                    description_lines.append(clean_bullet)
                j += 1
                
            current_internship = {
                "company": company,
                "role": role,
                "duration": duration,
                "description": " ".join(description_lines)
            }
            i = j
        else:
            i += 1
            
    if current_internship:
        internships_list.append(current_internship)
        
    return internships_list


def extract_cgpa(text: str) -> float:
    """
    Parses CGPA or GPA floats from the text, returning None if absent.
    """
    pattern1 = r'\b(?:cgpa|gpa|g\.p\.a|c\.g\.p\.a)[:\-\s]*(\d{1,2}(?:\.\d{1,2})?)'
    pattern2 = r'(\d{1,2}\.\d{1,2})\s*(?:/10|cgpa|gpa)'
    
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
            
    pct_match = re.search(r'(\d{2}(?:\.\d{1,2})?)\s*%', text)
    if pct_match:
        try:
            return float(pct_match.group(1))
        except ValueError:
            pass
            
    return None


def classify_experience_level(internships_count: int, projects_count: int, skills_count: int) -> str:
    """
    Categorizes the candidate's development index: Beginner, Intermediate, or Advanced.
    """
    if internships_count >= 2:
        return "Advanced"
    elif internships_count == 1 or projects_count >= 2:
        return "Intermediate"
    else:
        return "Beginner"


def parse_college_resume_intelligent(pdf_path: str) -> Dict[str, any]:
    """
    Combines rule-based lookups with a token sequence classifier (spaCy).
    Screens adjacent sentence tokens to verify skill classification and implements
    a strict filtering layer to discard institutional definitions.
    Generates a full Talent Graph student profile, returning null for absent elements.
    """
    raw_text = extract_text_with_spatial_bounds(pdf_path)
    clean_text = clean_and_normalize_text(raw_text)
    
    doc = nlp(clean_text)
    
    # 1. Segment structural sections
    sections = split_resume_into_sections(clean_text)
    
    # 2. Extract Personal Details
    links = extract_links_from_pdf(pdf_path)
    name = extract_name(doc, clean_text)
    email = extract_email(clean_text)
    phone = extract_phone(clean_text)
    
    if not email:
        for link in links:
            if link.startswith("mailto:"):
                email = link[7:]
                break
                
    github = extract_social_link(links, clean_text, "github.com", r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+')
    linkedin = extract_social_link(links, clean_text, "linkedin.com", r'(?:https?://)?(?:www\.)?linkedin\.com/(?:in|pub)/[a-zA-Z0-9_-]+')
    
    personal_details = {
        "name": name,
        "email": email,
        "phone": phone,
        "github": github,
        "linkedin": linkedin
    }
    
    # 3. Parse Technical Entities
    skills: Set[str] = set()
    domains: Set[str] = set()
    competencies: Set[str] = set()
    
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

    # 4. Extract Structural Talent Graph Profile Fields
    projects_list = extract_projects_structured(sections["PROJECTS"])
    internships_list = extract_internships_structured(sections["EXPERIENCE"])
    
    # Parse certifications, merging continuation lines
    certifications_list = []
    current_cert = ""
    for line in sections["CERTIFICATIONS"]:
        line_clean = line.strip()
        if not line_clean:
            continue
        if line_clean.startswith("* ") or line_clean.startswith("- ") or line_clean.startswith("• ") or line_clean.startswith("➢ "):
            if current_cert:
                certifications_list.append(current_cert)
            current_cert = re.sub(r'^[➢➢\-\*\•\s\u27a2]+', '', line_clean).strip()
        else:
            if current_cert:
                current_cert += " " + line_clean
            else:
                current_cert = line_clean
    if current_cert:
        certifications_list.append(current_cert)
            
    cgpa_val = extract_cgpa(clean_text)
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


if __name__ == "__main__":
    resume_path = "./Resume.pdf"
    print(f"Initializing parsing run on: {resume_path}")
    try:
        profile = parse_college_resume_intelligent(resume_path)
        print("✓ Extraction completed successfully. Materialized Payload:")
        print(json.dumps(profile, indent=4))
    except Exception as e:
        print(f"🚨 Parsing failed: {e}")
