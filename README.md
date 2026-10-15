# AI Resume Analyzer & Job Matching System

A recruiter decision-support tool. A recruiter provides a job description and uploads multiple resumes. The system extracts structured information, calculates an explainable match score for each candidate, ranks the candidates, and can generate an AI explanation of each result.

The system assists the recruiter. It does not make hiring decisions.

## Status

**Phases 0 through 10 Complete.** The entire Full Specification Stack is implemented and verified end-to-end:
- 60/60 unit, integration, and E2E acceptance tests passing.
- Performance benchmarks validated against all PRD targets (20 resumes in ~7s, 50 resumes in ~15s).
- Full UI workflow (Job Description review, batch upload, live progress polling, candidate ranking, grounded AI explanations, and cascade deletion).

## Tech Stack (Full Specification)

* **Backend:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic
* **Frontend:** React 19, Vite, Tailwind CSS, Lucide icons
* **Database & Vectors:** PostgreSQL 16 (port 5433), ChromaDB (port 8001)
* **Background Processing:** Celery 5.4, Redis 7 (port 6379)
* **Document Processing:** PyPDF (`pypdf`), `python-docx`, regex, spaCy
* **Semantic Matching:** Sentence Transformers (`all-MiniLM-L6-v2`), ChromaDB
* **AI Explanations:** Ollama (local instruct model) / MockLLMService
* **Testing & Quality:** pytest, ruff, GitHub Actions CI
* **Environment:** Docker and Docker Compose

## Documentation

The project specifications and implementation plans are organized in the `docs/` directory:

* [`docs/PRD.md`](docs/PRD.md): Product requirements, fairness, retention, and matching criteria
* [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): System architecture, layer boundaries, and ownership
* [`docs/API.md`](docs/API.md): REST API contracts, status models, and error schemas
* [`docs/DATABASE.md`](docs/DATABASE.md): PostgreSQL entities, constraints, and relational schemas
* [`docs/DESIGN.md`](docs/DESIGN.md): Recruiter UI guidelines, design tokens, and components
* [`docs/RULES.md`](docs/RULES.md): Non-negotiable architectural, fairness, and coding rules
* [`docs/TASKS.md`](docs/TASKS.md): Step-by-step task breakdown and implementation roadmap

## Repository Layout

```text
.
├── docs/                 project specification documents
├── backend/
│   ├── api/              FastAPI REST route controllers
│   ├── core/             config, database session, logging, error handling
│   ├── schemas/          shared Pydantic models & contracts
│   ├── services/         application, scoring, extraction & cleanup services
│   ├── repositories/     database models & repositories
│   ├── worker/           Celery background tasks & watchdog routines
│   └── migrations/       Alembic database migrations
├── ui/                   React + Vite frontend (Tailwind CSS)
├── tests/                unit, integration, and end-to-end acceptance tests
├── scripts/              performance benchmarks and evaluation runners
├── data/                 synthetic evaluation seed datasets
├── docker-compose.yml    local services (Postgres:5433, Redis:6379, ChromaDB:8001)
├── .env.example          environment configuration template
└── README.md
```

## Quickstart & Local Setup

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Docker Desktop

### 2. Infrastructure Services (Docker)
```bash
docker compose up -d
```
*Note: PostgreSQL is exposed on port `5433` (to avoid port conflicts), Redis on `6379`, and ChromaDB on `8001`.*

### 3. Backend Setup
```bash
# Virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows (or source .venv/bin/activate on Unix)
pip install -r requirements.txt

# Run Database Migrations
alembic upgrade head

# Start Celery Background Worker
celery -A backend.worker.celery_app.celery_app worker --loglevel=info -P solo -Q resume_queue,explanation_queue

# In a separate terminal: Start FastAPI API Server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
API docs are available at `http://localhost:8000/docs`.

### 4. Frontend Setup
```bash
cd ui
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

## Running Tests

Run the complete test suite (60 tests covering extraction, DB, matching, Celery, API, AI explanations, and E2E acceptance scenarios):
```bash
pytest -v
```

## Performance Benchmarks (REL-01)

Run the automated performance and throughput benchmark:
```bash
python scripts/benchmark_performance.py
```

### Benchmark Results
| Benchmark Scenario | Measured | PRD Target | Status |
| :--- | :--- | :--- | :--- |
| **20 Resumes End-to-End Processing** | **7.03s** | $\le$ 60.0s | **PASS** |
| **50 Resumes End-to-End Processing** | **15.13s** | $\le$ 150.0s | **PASS** |
| **Single Candidate AI Explanation** | **0.06s** | $\le$ 15.0s | **PASS** |

## Data & Privacy Rules

* Never commit real candidate resumes, personal data, secrets, or `.env` files.
* Tests and evaluation data use synthetic or anonymized data only.
* Raw uploaded resumes are automatically deleted from storage immediately following text extraction.
* Candidate names and contact details are excluded from all ranking computations, matching models, and vector stores.
* Deleting an analysis cascades across database records and purges isolated ChromaDB vector collections.