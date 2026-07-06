# Resume Analyzer & Information Extractor

A production-ready, Docker-based FastAPI microservice and experimentation suite that extracts structured information from resume PDFs (from remote URLs or local paths) and structures it into a comprehensive talent graph JSON response.

---

## 1. Project Directory Structure

This repository uses a single-repo architecture that separates experimentation (Jupyter notebooks), production business logic, API deployment, tests, and models/datasets.

```text
ResumeAnalyzer/
│
├── api/
│   └── app.py                  # FastAPI server (routing layer only)
│
├── src/                        # Core production modules
│   ├── downloader/             # Remote file downloader (GitHub, GDrive, HTTP URLs)
│   ├── extractor/              # PDF spatial layout text extractor (PyMuPDF)
│   ├── parser/                 # Resume segmentation and spaCy entity extraction
│   ├── pipeline/               # E2E resume parser orchestration pipeline
│   └── schemas/                # Pydantic schemas (request/response validation)
│
├── notebooks/
│   └── test.ipynb              # Experimentation notebook importing from src/
│
├── tests/                      # Unit and integration tests
│   ├── test_downloader.py
│   ├── test_extractor.py
│   ├── test_parser.py
│   └── test_pipeline.py
│
├── data/                       # Datasets and test documents
│   ├── Resume.pdf              # Sample resume PDF
│   └── sample_output.json      # Sample JSON output
│
├── models/
│   └── README.md               # Placeholder for local model files
│
├── Dockerfile                  # Docker configuration for API deployment
├── requirements.txt            # Unified package dependencies
├── pyproject.toml              # Project packaging configuration
└── README.md                   # This documentation file
```

---

## 2. API Documentation

When the service is running, it exposes a Swagger UI for interactive testing.

* **API Documentation URL**: `http://localhost:7860/docs` (locally) or `https://<space-name>.hf.space/docs` (on Hugging Face Spaces)

### Endpoints

#### A. Health Check
* **Path**: `GET /`
* **Response**:
  ```json
  {
    "status": "running"
  }
  ```

#### B. Parse Resume
* **Path**: `POST /parse`
* **Content-Type**: `application/json`
* **Request Body**:
  ```json
  {
    "url": "https://drive.google.com/file/d/1C8svOrGqiFxDFD8IfNid2sAFG54VOdva/view"
  }
  ```
* **Response**: Structured talent graph JSON. Refer to `data/sample_output.json` for details.

---

## 3. Local Execution & Testing

### Prerequisites
Make sure you have Python 3.9+ installed (developed on Python 3.13).

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

2. **Run Tests**:
   ```bash
   pytest
   ```

3. **Start the API Server**:
   ```bash
   uvicorn api.app:app --host 0.0.0.0 --port 7860 --reload
   ```

4. **Verify Locally**:
   Open `http://localhost:7860/docs` in your browser.

---

## 4. Deployment Instructions

To deploy this service to Hugging Face Spaces:

### Step 1: Create a Space on Hugging Face
1. Log in to your [Hugging Face Account](https://huggingface.co/).
2. Navigate to **Spaces** and click **Create new Space**.
3. Choose a name (e.g., `resume-parser`).
4. Select the **Docker** SDK.
5. Select the **Blank** template.
6. Select **Public** visibility.
7. Click **Create Space**.

### Step 2: Push Code to Hugging Face Space Git Repository
You can push the files to Hugging Face Space using Git:

```bash
git init
git add .
git commit -m "Refactored single-repository resume parser service"
git remote add origin https://huggingface.co/spaces/<your-username>/<your-space-name>
git branch -M main
git push -f origin main
```


