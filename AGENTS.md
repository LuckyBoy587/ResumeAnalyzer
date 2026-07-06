# Project Architectural Rules

This repository enforces a strict single-repository architecture. Follow these rules to ensure clean separation of concerns and maintain a zero-duplication workflow.

---

## Rules

### Rule 1: Production Business Logic belongs in `src`
All reusable core functionality (such as downloader utilities, text extraction filters, spacy parser heuristics, and schemas) must reside under the `src` directory.

### Rule 2: Notebooks must import from `src`
Jupyter notebooks (`notebooks`) are for experimentation, prototyping, and validation. They must not duplicate production logic. Once a prototype works, refactor the code into `src` and import it into the notebook:
```python
from src.pipeline.resume_parser import parse_resume
```

### Rule 3: API Layer must import from `src`
The API (`api/app.py`) is a thin routing and orchestration wrapper only. It must not contain parsing, cleaning, or extraction logic. It must consume the unified pipeline and schemas from `src`:
```python
from src.pipeline.resume_parser import parse_resume
from src.schemas.pydantic_models import ParseRequest
```

### Rule 4: No Duplicate Implementations
There must be exactly one source of truth for each feature. Any changes to parsing, downloading, or extraction logic must be made inside `src` so that both the notebooks and the API benefit automatically.

### Rule 5: Implement `src` first
When writing a new feature, implement and test it in `src` first, or prototype it in a notebook and immediately migrate the verified code to `src`.

---

## Directory Structure

```text
project-root/
├── notebooks/       # Jupyter notebooks (experimentation / dev workflows)
├── src/             # Production business logic (downloader, extractor, parser, pipeline, schemas)
├── api/             # API routing layer (FastAPI endpoints only)
├── tests/           # Unit and Integration test suites (pytest)
├── models/          # Local model files and placeholders
├── data/            # Datasets and test documents
├── Dockerfile       # Container definition for deployment
└── requirements.txt # Unified dependencies
```

## Rules

This project is intended to be run on Google Colab servers. 
Do not try to run it on my local machine.
Do not run any bash commands to execute code or install dependencies.