import os
import logging
import json
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_normalized_db_url() -> str:
    """
    Normalizes the database URL, replacing postgres:// with postgresql:// if needed.
    """
    url = os.getenv("DATABASE_URL") or DATABASE_URL
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url

def get_db_connection():
    """
    Creates and returns a new psycopg2 connection using the normalized DATABASE_URL.
    """
    url = get_normalized_db_url()
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set.")
    if "sslmode" not in url and "localhost" not in url and "127.0.0.1" not in url:
        return psycopg2.connect(url, sslmode="require")
    return psycopg2.connect(url)

def init_db():
    """
    Initializes the database by creating the resumes table if it does not exist.
    """
    schema_sql = """
    CREATE TABLE IF NOT EXISTS resumes (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      candidate_name text,
      email text UNIQUE,
      phone text,
      github_url text,
      linkedin_url text,
      experience_level text,
      cgpa numeric(3,2),
      skills text[] DEFAULT '{}',
      domains text[] DEFAULT '{}',
      competencies text[] DEFAULT '{}',
      raw_resume_json jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    );
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()
        logger.info("Database initialized successfully: resumes table is ready.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def save_resume_to_db(parsed_data: dict) -> dict:
    """
    Inserts or updates (upserts) a parsed resume into the database using email as the unique key.
    """
    personal_details = parsed_data.get("personal_details") or {}
    
    # Extract searchable fields
    candidate_name = personal_details.get("name")
    email = personal_details.get("email")
    if email and isinstance(email, str):
        email = email.strip()
        if not email:
            email = None
    else:
        email = None
        
    phone = personal_details.get("phone")
    github_url = personal_details.get("github")
    linkedin_url = personal_details.get("linkedin")
    
    experience_level = parsed_data.get("experience_level")
    cgpa = parsed_data.get("cgpa")
    
    # Ensure arrays are lists
    skills = parsed_data.get("skills") or []
    domains = parsed_data.get("domains") or []
    competencies = parsed_data.get("competencies") or []
    
    if not isinstance(skills, list):
        skills = [skills] if skills else []
    if not isinstance(domains, list):
        domains = [domains] if domains else []
    if not isinstance(competencies, list):
        competencies = [competencies] if competencies else []

    logger.info(f"DB insert/update start for candidate: {candidate_name} ({email or 'No Email'})")

    upsert_sql = """
    INSERT INTO resumes (
      candidate_name,
      email,
      phone,
      github_url,
      linkedin_url,
      experience_level,
      cgpa,
      skills,
      domains,
      competencies,
      raw_resume_json
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (email) DO UPDATE SET
      candidate_name = EXCLUDED.candidate_name,
      phone = EXCLUDED.phone,
      github_url = EXCLUDED.github_url,
      linkedin_url = EXCLUDED.linkedin_url,
      experience_level = EXCLUDED.experience_level,
      cgpa = EXCLUDED.cgpa,
      skills = EXCLUDED.skills,
      domains = EXCLUDED.domains,
      competencies = EXCLUDED.competencies,
      raw_resume_json = EXCLUDED.raw_resume_json,
      updated_at = now()
    RETURNING id;
    """

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # psycopg2.extras.Json automatically handles serialization
            cur.execute(
                upsert_sql,
                (
                    candidate_name,
                    email,
                    phone,
                    github_url,
                    linkedin_url,
                    experience_level,
                    cgpa,
                    skills,
                    domains,
                    competencies,
                    Json(parsed_data)
                )
            )
            row = cur.fetchone()
            db_id = str(row[0]) if row else None
        conn.commit()
        logger.info(f"DB insert/update success for candidate: {candidate_name} ({email or 'No Email'}) with DB ID: {db_id}")
        return {"id": db_id, "status": "persisted"}
    except Exception as e:
        logger.error(f"DB insert/update failure for candidate: {candidate_name} ({email or 'No Email'}). Error: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()
