# AI Resume Analyzer & Job Matching System

A recruiter decision-support tool. A recruiter provides a job description and uploads multiple resumes. The system extracts structured information, calculates an explainable match score for each candidate, ranks the candidates, and can generate an AI explanation of each result.

The system assists the recruiter. It does not make hiring decisions.

## Status

**Phase 1 In Progress.** The specification is approved, and we are implementing the Full Specification Stack across the roadmap defined in `TASKS.md`.

## Tech Stack (Full Specification)

* **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic
* **Frontend:** React, Vite, Tailwind CSS
* **Database & Vectors:** PostgreSQL, ChromaDB
* **Background Processing:** Celery, Redis
* **Document Processing:** PyPDF (`pypdf`), `python-docx`, regex, spaCy
* **Semantic Matching:** Sentence Transformers (`all-MiniLM-L6-v2`), ChromaDB
* **AI Explanations:** Ollama (local instruct model)
* **Testing & Quality:** pytest, ruff, GitHub Actions CI
* **Environment:** Docker and Docker Compose

## Repository Layout (Proposed)

The layout is confirmed in task `SET-01`.

```text
.
├── docs/                 project documents listed above
├── backend/
│   ├── schemas/          shared Pydantic models
│   ├── services/         application services, matching, extraction, LLM adapter
│   ├── repositories/     database access
│   ├── worker/           background worker loop
│   └── migrations/       Alembic migrations
├── ui/                   Streamlit app (display and input only)
├── tests/
├── data/                 synthetic evaluation data only
├── docker-compose.yml
├── .env.example          placeholder values only
└── README.md
```

Rules for the layout: all logic lives in `backend/`, and nothing outside `ui/` imports Streamlit.

## Prerequisites

* Python (version to be confirmed in `SET-02`)
* Docker and Docker Compose
* Git
* Enough memory and disk space to run a local Ollama model (depends on the model chosen)

## Setup

To be completed as the setup tasks finish. Each step below becomes a documented command.

1. Clone the repository.
2. Create a virtual environment and install dependencies (`SET-02`).
3. Copy `.env.example` to `.env` and fill in local values. Never commit `.env` (`SET-02`).
4. Start PostgreSQL, ChromaDB, and Ollama with Docker Compose (`SET-04`).
5. Run the database migrations (`SET-06`).
6. Start the worker process (`BG-01`).
7. Start the Streamlit app (`SET-03`).
8. Run the tests (`SET-05`).

## Team and Ownership

* **Person 1: Document Intelligence.** Extraction, skill normalization, job description requirements, PII scrubbing, the upload service, the seed dataset, and test and CI setup.
* **Person 2: Matching, Orchestration and Persistence.** Database, Profile Builder, scoring, ranking, embeddings, ChromaDB, the worker, and the analysis services.
* **Person 3: Interface and AI.** Streamlit screens, the service interface types, and all LLM work (Ollama, prompts, output validation, explanations).

Details and the shared handoffs are in `ARCHITECTURE.md` Section 3 and `MVP-LEAN.md` Section 6.

## Working Agreements

* Work in small tasks from `TASKS.md`, on branches, merged through pull requests.
* Every pull request needs a reviewer who is not the author.
* A change in someone else's area needs that owner's approval. A change to the shared schemas needs both Person 1 and Person 2.
* Update the relevant document before changing behavior it describes (`RULES.md` Section 25).
* Feature work starts only after the specification is approved (`DOC-04`).

## Data and Privacy Rules

* Never commit real candidate resumes, personal data, secrets, or `.env` files.
* Tests and evaluation data use synthetic, anonymized, or consented data only.
* Never paste real candidate data into external AI tools.
* Logs must not contain resume text or personal information.
* The MVP runs in a controlled environment. Do not deploy it publicly with real candidate data, and do not expose it without authentication.

## Known Limitations (Lean MVP)

* No public API and no React interface yet.
* The interface uses Streamlit's default look and is not tuned for mobile or full accessibility.
* Recovery from rare failures is simpler than in the full design. The finalization retry counter resets when the worker restarts, and expired uploads and orphaned vector collections are not handled automatically.
* Quality results come from a small seed dataset and are indicative only.
* Performance is verified only up to 20 resumes and was not benchmarked.
* Explanation quality was checked manually on a small sample.

## Roadmap

The order of work is in `TASKS.md`, with the lean scope marked on each task. After the lean MVP, the suggested upgrade path is in `MVP-LEAN.md` Section 12: FastAPI routes, the full watchdog and recovery tests, the orphaned-vector sweep, the full dataset and benchmarks, and then the React frontend.
