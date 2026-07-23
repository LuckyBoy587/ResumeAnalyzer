import os
import logging
import time

import uvicorn
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from src.schemas.pydantic_models import ParseRequest, ParseResponse
from src.pipeline.resume_parser import parse_resume

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("app")

app = FastAPI(
    title="Resume Parser & Embedding API",
    description="A FastAPI microservice to parse structured resume details and compute 384d sentence embeddings.",
    version="1.1.0"
)


@app.on_event("startup")
def startup_event():
    """
    Optional database schema initialization on startup.
    Failure to connect to DB does not block microservice startup.
    """
    logger.info("Application starting up...")
    if os.getenv("DATABASE_URL"):
        try:
            from src.database.db import init_db
            init_db()
        except Exception as e:
            logger.warning(f"Optional database initialization skipped or failed: {e}")


@app.get("/", summary="Health Check")
def health_check():
    """
    Service health check endpoint.
    """
    return {"status": "running"}


@app.get("/health/db", summary="Database Health Check")
def db_health_check():
    """
    Checks connection to the database (if configured).
    """
    try:
        from src.database.db import get_db_connection
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
        conn.close()
        return {"database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"database": "disconnected", "error": str(e)}
        )


@app.post("/parse", response_model=ParseResponse, summary="Parse Resume and Generate Embedding")
def parse_resume_endpoint(request: ParseRequest):
    """
    Accepts a resume PDF URL or local path, extracts text, parses structured entities,
    builds canonical embedding text, computes a 384d vector embedding, and returns pure JSON payload.
    Database persistence is delegated to the primary caller backend.
    """
    logger.info("Request Received")
    start_time = time.time()
    
    url = request.url
    include_embedding = request.include_embedding
    
    try:
        # Core stateless parsing & embedding pipeline
        response_payload = parse_resume(url, include_embedding=include_embedding)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Response Returned successfully (Processing time: {elapsed_time:.3f}s)")
        
        return response_payload
        
    except ValueError as e:
        logger.error(f"Validation error processing resume: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(e)}
        )
    except RuntimeError as e:
        logger.error(f"Runtime error processing resume: {str(e)}")
        error_msg = str(e)
        if "download" in error_msg.lower() or "unable to download" in error_msg.lower():
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"error": "Unable to download resume"}
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": error_msg}
        )
    except Exception as e:
        logger.error(f"Unhandled error processing resume: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Internal server error: {str(e)}"}
        )

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)