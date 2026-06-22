import os
import logging
import uuid
from typing import Dict, Any
from src.downloader.downloader import download_file_from_url
from src.extractor.extractor import extract_text_from_pdf
from src.parser.parser import parse_resume_to_entities, detect_file_type

logger = logging.getLogger(__name__)

def parse_resume(url: str) -> Dict[str, Any]:
    """
    Downloads the resume from the URL (or uses the local path),
    detects the file type, extracts text, runs the NER/parser, and returns structured JSON.
    Guarantees the cleanup of any downloaded temporary files.

    Args:
        url (str): Remote URL (GDrive, GitHub, direct) or local file path to the resume.

    Returns:
        dict: Structured resume data in JSON format.
    """
    is_url = url.startswith("http://") or url.startswith("https://")
    local_path = url

    if is_url:
        temp_filename = f"temp_{uuid.uuid4().hex}.pdf"
        logger.info(f"Downloading resume from URL: {url} to {temp_filename}")
        local_path = download_file_from_url(url, temp_filename)
    else:
        logger.info(f"Using local file path: {url}")

    try:
        # 1. Detect file type
        file_type = detect_file_type(local_path)
        if file_type != "pdf":
            logger.error(f"Validation failed. Unsupported file type: {file_type.upper()}")
            raise ValueError(f"Unsupported file type: {file_type.upper()}. Only PDF resumes are supported.")

        # 2. Extract text
        logger.info(f"Extracting text from: {local_path}")
        clean_text = extract_text_from_pdf(local_path)
        
        # 3. Parse entities
        logger.info("Parsing structured entities from text")
        result = parse_resume_to_entities(local_path, clean_text=clean_text)
        logger.info("Parsing completed successfully.")
        return result
        
    finally:
        if is_url and os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.info(f"Temporary file {local_path} deleted successfully.")
            except Exception as e:
                logger.warning(f"Could not remove temporary file {local_path}: {e}")
                
