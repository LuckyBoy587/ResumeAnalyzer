import os
import re
from pydantic import BaseModel, Field, validator

from typing import Dict, Any, List, Optional

class ParseRequest(BaseModel):
    url: str = Field(
        ...,
        description="The remote URL of the resume PDF (Google Drive, GitHub, direct) or local path.",
        example="https://drive.google.com/file/d/1C8svOrGqiFxDFD8IfNid2sAFG54VOdva/view"
    )
    include_embedding: bool = Field(
        default=True,
        description="Whether to generate and return a 384-dimensional sentence embedding for the resume."
    )

    @validator('url')
    def validate_url(cls, v):
        url_val = v.strip()
        if not url_val:
            raise ValueError("URL or file path cannot be empty.")
            
        # Check if it looks like a URL
        is_http = url_val.startswith("http://") or url_val.startswith("https://")
        
        if is_http:
            # Simple URL format validation
            url_regex = re.compile(
                r'^(?:http|ftp)s?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            if not re.match(url_regex, url_val):
                raise ValueError("Invalid URL format.")
                
            # Proactively reject known unsupported extensions from URL if present
            path_part = url_val.split('?')[0].split('#')[0]
            _, ext = os.path.splitext(path_part.lower())
            if ext and ext != '.pdf':
                raise ValueError(f"Unsupported file type '{ext}'. Only PDF resumes are supported.")
        else:
            # If not a URL, must be an existing local file path
            if not os.path.exists(url_val):
                raise ValueError("Input must be a valid URL or an existing local PDF file path.")
                
            _, ext = os.path.splitext(url_val.lower())
            if ext != '.pdf':
                raise ValueError(f"Unsupported local file type '{ext}'. Only PDF resumes are supported.")
                
        return url_val


class EmbeddingMetadata(BaseModel):
    model_name: str = Field(..., description="Name of the embedding model used")
    dimension: int = Field(..., description="Dimension of the embedding vector")
    status: str = Field(..., description="Generation status: 'success', 'failed', or 'skipped'")
    char_count: int = Field(..., description="Character count of the embedding text")
    error_message: Optional[str] = Field(None, description="Error message if generation failed")
    generated_at: str = Field(..., description="ISO timestamp of embedding generation")


class ParseResponse(BaseModel):
    parsed_resume: Dict[str, Any] = Field(..., description="Structured resume entities and sections")
    embedding_text: str = Field(..., description="Canonical text representation generated for embedding")
    embedding_metadata: EmbeddingMetadata = Field(..., description="Metadata related to embedding generation")
    embedding: Optional[List[float]] = Field(None, description="384-dimensional vector embedding (null if failed or skipped)")

