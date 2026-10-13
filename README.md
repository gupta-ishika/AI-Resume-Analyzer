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
│   ├── core/             config, database session, logging, error handling
│   ├── schemas/          shared Pydantic models
│   ├── services/         application & extraction services
│   ├── repositories/     database access & repositories
│   ├── worker/           Celery background tasks
│   └── migrations/       Alembic database migrations
├── ui/                   React + Vite frontend (Tailwind CSS)
├── tests/                unit and integration test suites
├── data/                 synthetic evaluation seed datasets
├── docker-compose.yml    local services (Postgres, Redis, ChromaDB, Ollama)
├── .env.example          environment configuration template
└── README.md
```

All business logic lives in `backend/`, and presentation is decoupled inside `ui/`.

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
7. Start the React frontend application (`SET-03`).
8. Run the tests (`SET-05`).

## Team and Ownership

* **Person 1: Document Intelligence.** Extraction, skill normalization, job description requirements, PII scrubbing, the upload service, the seed dataset, and test and CI setup.
* **Person 2: Matching, Orchestration and Persistence.** Database, Profile Builder, scoring, ranking, embeddings, ChromaDB, the worker, and the analysis services.
* **Person 3: Interface and AI.** FastAPI routes, React UI, the service interface types, and all LLM work (Ollama, prompts, output validation, explanations).

Details and the shared handoffs are in `ARCHITECTURE.md` Section 3.

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

## Roadmap

The order of work is sequentially tracked across the task phases in [`docs/TASKS.md`](docs/TASKS.md).