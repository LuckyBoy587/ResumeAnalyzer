import os
import re
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

def download_file_from_url(url: str, output_path: str = "temp_resume.pdf") -> str:
    """
    Downloads a file from a Google Drive, GitHub, or direct URL,
    and returns the local file path. If the input is an existing local path,
    returns it directly.

    Args:
        url (str): The URL or local path to the resume.
        output_path (str): The local path where the file should be saved.

    Returns:
        str: The path to the downloaded local file.

    Raises:
        ValueError: If the URL or path is invalid.
        RuntimeError: If the download fails.
    """
    logger.info(f"Checking input path/URL: {url}")
    
    # If it is a local path that exists, return it
    if os.path.exists(url):
        logger.info(f"Using existing local file: {url}")
        return url

    # Check if it looks like a URL
    if not (url.startswith("http://") or url.startswith("https://")):
        logger.warning(f"Provided path does not exist locally and is not a valid URL schema: {url}")
        raise ValueError(f"File path does not exist locally and is not a valid URL: {url}")

    try:
        # 1. Google Drive URL pattern matching
        gd_match = re.search(
            r'(?:drive\.google\.com/(?:file/d/|open\?id=|uc\?id=|uc\?export=download&id=)|docs\.google\.com/file/d/)([a-zA-Z0-9_-]+)',
            url
        )
        if gd_match:
            file_id = gd_match.group(1)
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            logger.info(f"Detected Google Drive link. File ID: {file_id}. Download URL: {download_url}")

            session = requests.Session()
            response = session.get(download_url, stream=True)

            confirm_token = None
            for key, value in response.cookies.items():
                if key.startswith('download_warning'):
                    confirm_token = value
                    break

            if confirm_token:
                logger.info("Handling Google Drive download warning confirmation token.")
                download_url += f"&confirm={confirm_token}"
                response = session.get(download_url, stream=True)

            response.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logger.info(f"Successfully downloaded Google Drive file to: {output_path}")
            return output_path

        # 2. GitHub URL pattern matching (converting web link to raw content link)
        github_match = re.search(r'github\.com/([^/]+)/([^/]+)/(?:blob|raw)/([^/]+)/(.+)', url, re.IGNORECASE)
        if github_match:
            user, repo, branch, path = github_match.groups()
            path = path.split('?')[0].split('#')[0]
            download_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"
            logger.info(f"Detected GitHub URL. Rewriting to raw content link: {download_url}")
        else:
            download_url = url

        # 3. Direct/fallback URL download
        logger.info(f"Downloading from: {download_url}")
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    
        logger.info(f"Successfully downloaded file to: {output_path}")
        return output_path

    except requests.RequestException as e:
        logger.error(f"Failed to download remote file from {url}: {str(e)}")
        raise RuntimeError(f"Unable to download resume from the provided URL: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during download: {str(e)}")
        raise
