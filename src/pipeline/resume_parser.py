import os
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from src.downloader.downloader import download_file_from_url
from src.extractor.extractor import extract_text_from_pdf
from src.parser.parser import parse_resume_to_entities, detect_file_type
from src.embedding.embedding_builder import build_embedding_text
from src.embedding.embedder import generate_embedding, DEFAULT_MODEL_NAME, DEFAULT_DIMENSION

logger = logging.getLogger(__name__)

def parse_resume(url: str, include_embedding: bool = True) -> Dict[str, Any]:
    """
    Downloads the resume from the URL (or uses local path), detects file type,
    extracts text, parses structured entities, builds embedding text, generates 384d vector embedding,
    and returns a unified payload.

    Args:
        url (str): Remote URL or local file path to the resume PDF.
        include_embedding (bool): Whether to compute and return vector embedding. Default is True.

    Returns:
        dict: Complete response payload with parsed_resume, embedding_text, embedding_metadata, and embedding.
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

        # 2. Extract raw clean text
        logger.info(f"Extracting text from: {local_path}")
        clean_text = extract_text_from_pdf(local_path)
        
        # 3. Parse structured resume entities
        logger.info("Parsing structured entities from text")
        parsed_resume = parse_resume_to_entities(local_path, clean_text=clean_text)
        logger.info("Parsing completed successfully.")

        # 4. Build canonical embedding text representation (Excluding PII & CGPA)
        embedding_text = build_embedding_text(parsed_resume, clean_text=clean_text)

        # 5. Generate sentence vector embedding
        vector = None
        now_iso = datetime.now(timezone.utc).isoformat()

        if include_embedding:
            logger.info("Generating dense 384-dimensional embedding vector...")
            vector, metadata = generate_embedding(embedding_text)
        else:
            logger.info("Skipping embedding generation (include_embedding=False).")
            metadata = {
                "model_name": os.getenv("EMBEDDING_MODEL_NAME", DEFAULT_MODEL_NAME),
                "dimension": int(os.getenv("EMBEDDING_DIMENSION", str(DEFAULT_DIMENSION))),
                "status": "skipped",
                "char_count": len(embedding_text),
                "error_message": None,
                "generated_at": now_iso
            }

        return {
            "parsed_resume": parsed_resume,
            "embedding_text": embedding_text,
            "embedding_metadata": metadata,
            "embedding": vector
        }
        
    finally:
        if is_url and os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.info(f"Temporary file {local_path} deleted successfully.")
            except Exception as e:
                logger.warning(f"Could not remove temporary file {local_path}: {e}")
