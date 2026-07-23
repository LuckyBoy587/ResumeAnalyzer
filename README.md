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

### Deploying to Heroku

#### Method A: Heroku CLI / Git Deployment (Standard Buildpack)

1. **Log in to Heroku**:
   ```bash
   heroku login
   ```

2. **Create a Heroku App**:
   ```bash
   heroku create resume-analyzer-api
   ```

3. **Provision PostgreSQL Addon**:
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

4. **Deploy via Git**:
   ```bash
   git add .
   git commit -m "Configure Heroku deployment"
   git push heroku main
   ```

5. **Verify Deployment**:
   ```bash
   heroku open
   ```

#### Method B: Container / Docker Deployment (`heroku.yml`)

1. **Set Heroku App Stack to Container**:
   ```bash
   heroku stack:set container -a resume-analyzer-api
   ```

2. **Deploy via Git**:
   ```bash
   git push heroku main
   ```

---

### Deploying to Hugging Face Spaces

1. **Create a Space on Hugging Face**: Choose **Docker** SDK with Blank template.
2. **Push Code**:
   ```bash
   git remote add hf https://huggingface.co/spaces/<your-username>/<your-space-name>
   git push -f hf main
   ```



