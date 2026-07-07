import os
import logging
import time
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from src.schemas.pydantic_models import ParseRequest
from src.pipeline.resume_parser import parse_resume
from src.database.db import init_db, save_resume_to_db

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("app")

app = FastAPI(
    title="Resume Parser API",
    description="A FastAPI microservice to parse structured details from resume PDFs.",
    version="1.0.0"
)


@app.on_event("startup")
def startup_event():
    """
    Initialize the database schema on application startup.
    """
    logger.info("Application starting up. Initializing database schema...")
    try:
        init_db()
    except Exception as e:
        logger.critical(f"Database initialization failed during startup: {e}", exc_info=True)


@app.get("/", summary="Health Check")
def health_check():
    """
    Service health check endpoint.
    """
    return {"status": "running"}


@app.get("/health/db", summary="Database Health Check")
def db_health_check():
    """
    Checks connection to the database.
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


@app.post("/parse", summary="Parse Resume")
def parse_resume_endpoint(request: ParseRequest):
    """
    Accepts a resume URL, downloads and parses it, and returns structured resume data.
    """
    logger.info("Request Received")
    start_time = time.time()
    
    url = request.url
    
    try:
        # Core parsing logic delegated to production pipeline module
        parsed_data = parse_resume(url)
        logger.info("Resume parsing succeeded.")
        
        # Persist the parsed resume JSON to database
        save_resume_to_db(parsed_data)
        
        logger.info("NER Completed")
        elapsed_time = time.time() - start_time
        logger.info(f"Response Returned (Processing time: {elapsed_time:.3f}s)")
        
        return parsed_data
        
    except ValueError as e:
        logger.error(f"Validation error processing resume: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(e)}
        )
    except RuntimeError as e:
        logger.error(f"Runtime error processing resume: {str(e)}")
        # Specific error message for download failures as requested
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

