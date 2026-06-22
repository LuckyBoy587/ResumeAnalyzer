import os
import logging
import time
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from src.schemas.pydantic_models import ParseRequest
from src.pipeline.resume_parser import parse_resume

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


@app.get("/", summary="Health Check")
def health_check():
    """
    Service health check endpoint.
    """
    return {"status": "running"}


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
