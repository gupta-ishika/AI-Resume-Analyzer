# ARCHITECTURE.md

# AI Resume Analyzer & Job Matching System

## 1. Purpose and Goals

This document defines how the system is structured, how components interact, how processing runs, and who owns each part. The PRD defines what the product must do. This document defines how.

The architecture must provide:

* Clear separation between frontend, API, document intelligence, matching, orchestration, and AI explanation.
* Deterministic, explainable scoring and ranking.
* A scoring pipeline that cannot consume irrelevant personal attributes.
* Parallel, recoverable background processing of multiple resumes.
* Partial failure handling and recruiter-confirmed JD requirements.
* Ranking available before AI explanations, with on-demand explanations per candidate.
* A controlled lifecycle for raw files, results, and vector data.
* Replaceable embedding, LLM, and task-execution implementations.
* Independently testable domain logic.

---

## 2. High-Level Architecture

```text
Recruiter → React Frontend
                 │ REST
                 ▼
            FastAPI API
                 │
                 ▼
        Application Services
        (orchestration, state)
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
 Document     Matching    Explanation
Intelligence   Engine      Service
     │           │           │
     │      ┌────┴────┐      ▼
     │      ▼         ▼    Ollama
     │  ChromaDB  PostgreSQL
     │
     └──── Celery workers ◄── Redis (broker)
```

Layers, top to bottom: presentation, API, application services, background execution, domain logic, persistence, model infrastructure. A layer should not bypass the one below it.

---

## 3. Ownership

**Person 1 — Document Intelligence**

* PDF/DOCX extraction, text cleaning, section detection
* Skill, experience, education, and project extraction
* JD requirement extraction
* All skill normalization and synonym handling
* Shared PII-detection utility (names, contact details, institutions) used by the Profile Builder
* Extraction failure classification and extraction benchmark

**Person 2 — Matching, Orchestration & Persistence**

* Shared integration contracts and analysis orchestrator
* Analysis state machine and background task coordination
* Profile Builder
* Matching engine, embeddings, ChromaDB, score calculation, ranking
* PostgreSQL schema, repositories, cleanup operations
* Fairness and matching evaluation infrastructure

**Person 3 — API, Frontend & AI Explanation**

* FastAPI routes, request validation, response schemas
* React application and all UI states
* Ollama integration, prompt construction, output parsing, grounding validation
* AI explanation evaluation

**Shared early task — evaluation dataset.**
All three people build and label the dataset before parallel implementation starts. Person 1 leads extraction annotation, Person 2 leads matching and shortlist labels, and Person 3 prepares explanation review criteria. Person 1's extraction benchmark depends on it.

---

## 4. Frontend

React, Vite, and Tailwind CSS. The frontend handles presentation only and must contain no matching or scoring logic.

Main flow:

```text
Provide JD → Review / edit requirements → Upload resumes
→ Start analysis → Processing status → Ranked candidates
→ Candidate detail → Request AI explanation → Display explanation
```

It also provides failed-file and duplicate reporting, explanation status, saved analyses, and deletion.

---

## 5. API Layer

FastAPI. Routes stay thin: validate the request, call an application service, return a response. No business logic in route handlers.

The API layer validates file type and size at upload time and computes the content hash (see Section 13).

Endpoints:

```text
POST   /api/analyses                                  create analysis with JD (upload or paste)
GET    /api/analyses                                  list saved analyses
GET    /api/analyses/{id}
GET    /api/analyses/{id}/status
DELETE /api/analyses/{id}

GET    /api/analyses/{id}/requirements
PUT    /api/analyses/{id}/requirements                review / edit / add requirements

POST   /api/analyses/{id}/resumes                     upload resumes
GET    /api/analyses/{id}/resumes                     list uploaded files with status and reason
POST   /api/analyses/{id}/start                       confirm requirements and start processing

GET    /api/analyses/{id}/candidates
GET    /api/analyses/{id}/candidates/{candidate_id}

POST   /api/analyses/{id}/candidates/{candidate_id}/explanation
GET    /api/analyses/{id}/candidates/{candidate_id}/explanation
```

Resumes are scoped to an analysis because duplicate detection, temporary files, tasks, and cleanup are all per analysis. The resume upload endpoint accepts one or more files per request, and the frontend may send small batches to show per-file progress. Exact request and response schemas belong in `API.md`.

Status response (concept):

```text
{ "status": "PROCESSING", "total": 18, "processed": 15, "successful": 12, "needs_review": 1, "failed": 2, "duplicates_excluded": 2 }
```

---

## 6. Document Intelligence

```text
PDF / DOCX → Validation → Text Extraction → Cleaning
→ Section Detection → Information Extraction
→ Normalization → Shared Pydantic Schema
```

The MVP uses non-LLM extraction: PyPDFLoader, python-docx, rules and regex, a skill dictionary with canonical normalization, and spaCy where useful.

Extraction is benchmarked early against the evaluation dataset. If it misses the PRD targets, the approach is revisited based on that evidence. LLM-based extraction is not part of the MVP architecture.

---

## 7. Data Contract

Person 1 and Person 2 communicate only through shared Pydantic schemas. The schemas are agreed and frozen before parallel implementation. Neither side creates a competing candidate or job representation.

Skill normalization belongs entirely to Person 1. Person 2 receives canonical skills and must not add another synonym layer.

---

## 8. Candidate, Job, and ScoringProfile

The extracted candidate object contains display data (name, contact information, other identifying details) plus extracted skills, experience, projects, and education. This full object is never passed to the matching engine.

The `ScoringProfile` is the only candidate representation allowed into matching:

```text
ScoringProfile
├── skills[]            (canonical)
├── experience[]
├── projects[]
├── education[]
└── job_relevant_text
```

It must not contain name, email, phone, photograph, age, gender indicators, marital status, religion, caste, other contact information, or institution names. The matching engine has no interface that accepts the full candidate object.

The job has a matching view as well:

```text
MatchingProfile
├── required_skills[]
├── preferred_skills[]
├── experience_requirements[]
├── education_requirements[]
├── explicit_requirements[]
└── job_relevant_text
```

### Profile Builder (Person 2)

The Profile Builder turns full candidate data into a safe `ScoringProfile`. It removes prohibited information. It does not decide which experience is relevant to a job. That is the matching engine's responsibility.

### Free-text scrubbing

`job_relevant_text` is built only from approved sections (experience responsibilities, project descriptions, technical skills). The raw resume is never concatenated into it.

Scrubbing is deterministic:

1. Remove every occurrence of the extracted name, email, phone number, and institution names, using the values already extracted from the same resume.
2. Remove other personal identifiers found by the shared PII-detection utility from Person 1.
3. Replace gendered pronouns and gendered terms with a neutral placeholder.

Institution names are excluded from semantic scoring by default. If the JD explicitly requires a specific institution or credential, that is handled as a structured education requirement, not through semantic similarity.

---

## 9. Matching Engine

```text
ScoringProfile + MatchingProfile
        ↓
Skill coverage (required, preferred)
Semantic relevance
Relevant experience
Education / explicit requirements
        ↓
Score breakdown → Final score → Ranking
```

Job-specific relevance is determined inside the matching engine. For example, a candidate with restaurant management, React development, and event organization experience is evaluated against a backend role by the engine, not by the Profile Builder.

Score weights are not locked. They are chosen and validated against the evaluation dataset.

Ranking uses these tie-breakers in order:

1. Required-skill coverage
2. Relevant-experience score
3. Semantic relevance
4. System-generated candidate ID, unrelated to personal attributes

### Semantic matching and embeddings

Semantic matching embeds the `ScoringProfile` text and the job text, never the raw resume.

The initial embedding model is `sentence-transformers/all-MiniLM-L6-v2`. It is benchmarked for ranking quality, latency, and memory use, and sits behind an `EmbeddingService` interface.

### ChromaDB

ChromaDB is retained for the MVP. Each analysis has its own collection (`analysis_<id>`), which gives isolation, easy cleanup, and no cross-analysis retrieval. If evaluation shows it adds no value, it can be reconsidered before production.

---

## 10. PostgreSQL

PostgreSQL is the source of truth for structured data: analyses and their state, job requirements, candidate data needed for review, matching results and score breakdowns, per-candidate explanation state and explanations, resume statuses, failure records, and processing metadata.

The detailed schema is defined in `DATABASE.md`.

---

## 11. Analysis Lifecycle

```text
REQUIREMENTS_PENDING → PROCESSING → RANKED
                          └──────→ FAILED
```

There is no analysis-level explanation state. Explanations belong to individual candidates (Section 15).

### Requirements review and start

1. `POST /analyses` creates the analysis and extracts requirements from the JD. If extraction is unreliable, the recruiter provides requirements manually.
2. While in `REQUIREMENTS_PENDING`, the recruiter edits requirements and uploads resumes.
3. `POST /analyses/{id}/start` validates that requirements are sufficient and at least one resume is `READY`, saves the confirmed requirements, moves the state to `PROCESSING`, and enqueues one task per `READY` resume. It returns promptly and does not wait for extraction, embeddings, or ranking.
4. No uploads are accepted after start, so the set of resumes is fixed.
5. The state change is a conditional update, so repeated start requests are safe. A second start finds the analysis already `PROCESSING` and receives a conflict response.

Resume processing never begins before requirements are confirmed.

### Deletion

An analysis cannot be deleted while it is `PROCESSING`. `DELETE /analyses/{id}` is rejected with a conflict error in that state. Deletion is allowed from `REQUIREMENTS_PENDING`, `RANKED`, and `FAILED`, so abandoned analyses can be removed. Blocking deletion during `PROCESSING` avoids cancellation and partial-cleanup complexity in the MVP. A repeated delete after the marker is set returns not found and changes nothing.

PostgreSQL and ChromaDB cannot share one atomic transaction, so deletion is a tracked, retryable operation and not an ordinary database cascade:

1. Mark the analysis as deletion-in-progress. This is a marker on the analysis, not a new lifecycle state.
2. Hide the analysis immediately from all listings and reads.
3. Delete the ChromaDB collection and embeddings and any remaining temporary files, retrying on failure.
4. Delete the database rows only after the vector data is gone.

If vector deletion fails, the marker stays and the cleanup job retries it. An analysis is never treated as fully deleted while its vector data remains.

---

## 12. Background Execution

* **Celery** runs the tasks and **Redis** is the broker.
* **Multiple worker processes** handle CPU-heavy extraction and embedding. The worker count is configurable and validated by benchmarking against the 50-resume target.
* There are two queues: one for resume processing and one for AI explanations, so slow LLM calls never block extraction.
* Task execution sits behind an interface so it can be replaced.

### Resume task

`process_resume(analysis_id, resume_id)`:

1. Extract text and canonical structured data.
2. Build the `ScoringProfile`.
3. Generate embeddings and run matching.
4. Persist the result.
5. Delete the raw file, whatever the outcome.
6. Record success or failure.

The task is idempotent, keyed by analysis and resume identity.

### Finalization

When a resume reaches a final status (success, failed, or needs review), the task atomically updates it and checks whether any resumes remain unfinished. Duplicates are rejected at upload and never queued, so they are not part of this check. The task that completes the last one enqueues a finalize step.

Finalization runs as one database transaction. It locks the analysis row, exits if the status is no longer `PROCESSING`, writes candidate ranks and labels, sets `RANKED`, and commits. A concurrent run waits for the lock, sees `RANKED`, and exits, so running it twice or at the same time has no extra effect. Unique constraints on rank and label are an additional safeguard. The analysis becomes `RANKED` only when the transaction commits, so a partial ranking is never visible.

As part of finalization, each candidate receives a display label such as `Candidate 01`. Labels are assigned once, by ordering candidates by their random candidate ID, so they never depend on rank, upload order, or filename. They are stored and never recomputed, so they stay the same when a saved analysis is reopened. Candidates have no label before this step. Labels are sequential and zero-padded (`Candidate 01`, `Candidate 02`, and so on), ordered by candidate ID. Assignment happens inside the finalization transaction and only for candidates that have no label yet, so repeating finalization never changes an existing label.

If every resume fails, the analysis still ends in `RANKED` with an empty ranking and the full failure list. `FAILED` is reserved for unrecoverable system-level errors such as the database being unavailable.

### Recovery

PostgreSQL status is the source of truth. Redis persistence and late task acknowledgement reduce task loss, but the design does not rely on them.

A watchdog periodically finds resumes of `PROCESSING` analyses that are not in a final state past the expected processing window and re-queues them. This also covers enqueue failure: if enqueueing fails after the analysis moved to `PROCESSING` (for example Redis is unavailable), the resumes stay unqueued and the watchdog re-queues them. The watchdog also resets stale `GENERATING` explanations to `FAILED`.

An analysis must not remain `PROCESSING` forever. If recovery is impossible, it is marked `FAILED` with an actionable reason.

### Claiming and stale work

A worker claims a resume with a conditional update from `READY` to `PROCESSING` and records the start time. If the claim fails, another worker already owns the resume and the task exits without processing it. This is how "never queued" is told apart from "in progress", and it prevents two workers from processing the same resume.

The watchdog uses two rules:

* A `READY` resume of a `PROCESSING` analysis that nobody has claimed within the claim window is re-queued.
* A `PROCESSING` resume whose start time is older than the window is treated as stale. It returns to `READY` for a limited number of retries, then becomes `FAILED` with a reason.

Redis unavailability during start and worker restarts are tested against these rules. No separate outbox mechanism is needed for the MVP.

### Lost finalization

The watchdog also detects analyses that remain `PROCESSING` after every associated resume has reached a final status, for example because the finalize task was lost or failed. It safely enqueues finalization again. Finalization is idempotent: repeating it never changes existing candidate labels and never duplicates match results.

### Finalization failure

Transient errors during finalization (database connection, lock timeout, queue) are retried with backoff, up to 2 automatic retries after the initial attempt (3 attempts in total). Any other error, or exhausted retries, marks the analysis `FAILED` with the reason `FINALIZATION_FAILED`. Because finalization is all-or-nothing, an analysis is never `RANKED` with a partial result.

Delivery problems are different from execution failures. A finalize task that was never delivered, or a worker lost before the task ran, is recovered by the watchdog and does not count as a failed attempt. Once an analysis is `FAILED`, the watchdog never enqueues finalization again. A failed analysis can still be deleted.

---

## 13. Duplicate Detection and Partial Failure

**Duplicates.**
The API computes the content hash when a file is uploaded. Within one analysis, only one canonical resume record may own a given content hash, enforced by a database constraint. A duplicate is recorded as a duplicate that references the canonical resume, is shown to the recruiter, and has its file deleted immediately. It creates no candidate and no task. The constraint is on the insert itself, so two concurrent uploads of the same content cannot both register as canonical.

**Upload limit.**
The limit of 50 applies to accepted resumes in an analysis. Duplicates and rejected files do not count. It is enforced at the database level so concurrent upload requests cannot exceed it, for example by locking the analysis row while accepted resumes are counted and registered.

**Resume statuses.**
A resume is created at upload as `READY`, `DUPLICATE`, or `REJECTED`. Only `READY` moves on: `PROCESSING`, then `SUCCESS`, `FAILED`, or `NEEDS_REVIEW`. `DUPLICATE` and `REJECTED` are final for processing and are never queued. Upload outcomes, including rejections, are persisted with the filename and reason so the recruiter can review them later. The contents of rejected files are never stored. The one later transition into `REJECTED` is expiry: a `READY` resume in a `REQUIREMENTS_PENDING` analysis whose temporary file passes the retention window becomes `REJECTED` with reason `UPLOAD_EXPIRED`.

`FAILED` belongs to the entity it describes: for an analysis it means an unrecoverable system-level error, for a resume a document-processing failure, and for an explanation a generation failure.

**Partial failure.**
Each resume is an independent unit. Failures are recorded with reasons and shown separately, valid candidates are ranked, and failed files never receive a low score. A document-level error never becomes an analysis-level failure. Only infrastructure failures do.

**Needs review.**
If extraction succeeds but the document structure is unreliable (PRD 14.4), the resume is recorded as a non-ranked result with the reason "needs review". It is shown separately with that reason, is never scored, and counts as a final status for finalization.

---

## 14. Raw File Lifecycle

```text
Upload → Validate → Hash → Temporary storage
→ Extraction attempt → Delete raw file
```

Deletion timing:

* A file rejected at upload (unsupported type or too large) is never retained.
* A duplicate's temporary file is deleted immediately at upload.
* An accepted file is deleted when its extraction attempt ends, regardless of outcome (success, corrupted, scanned or image-only, failed extraction, or needs review).
* Files left behind by interrupted processing are removed by the cleanup job.
* An uploaded job description file is deleted when requirement extraction ends, regardless of outcome. Only the extracted requirements and job-relevant text are saved.

Files wait in temporary storage between upload and start, so temporary storage has a maximum retention window. A cleanup job runs at startup and periodically. It finds files with no active processing record and deletes stale or orphaned ones, which covers crashes. In a `REQUIREMENTS_PENDING` analysis, a file that passes the retention window is deleted and its resume is marked `REJECTED` with reason `UPLOAD_EXPIRED`, so the recruiter sees it as expired and can upload it again.

Temporary storage is a shared volume accessible to both the API and the Celery worker containers. Files are stored under generated names. The original filename is never used as a storage path.

Downstream matching and explanations use structured data and matching evidence, never raw files.

---

## 15. AI Explanation

Owned by Person 3. The LLM explains results and never calculates or modifies scores.

### Per-candidate state

```text
NOT_REQUESTED → GENERATING → READY
                    └──────→ FAILED → (retry) GENERATING
```

* The move to `GENERATING` is an atomic conditional database update (only from `NOT_REQUESTED` or `FAILED`). Two simultaneous requests cannot both start generation.
* A timeout resets `GENERATING` to `FAILED` if the LLM call dies.
* A candidate already `GENERATING` or `READY` never triggers another LLM call.
* A failed explanation can be retried by a new request. A successful explanation is never regenerated in the MVP.

### Flow

```text
Request → atomic state change → build grounded context
→ call Ollama → parse → schema validation
→ grounding validation → persist → READY
```

Context is the candidate result, confirmed job requirements, score breakdown, and matching evidence. It excludes unnecessary identifying information.

### LLM runtime

Initial runtime is Ollama behind an `LLMService` abstraction. The model is chosen after benchmarking hardware needs, latency, explanation quality, and structured-output reliability.

Responses must pass the output parser, schema validation, and grounding validation. The explanation cannot introduce qualifications that are not in the extracted data.

---

## 16. Privacy and Network Exposure

* Raw files are deleted after the extraction attempt (Section 14).
* PostgreSQL stores only what is needed for review, matching results, explanations, and persistence.
* ChromaDB holds vectors only inside the analysis's own collection.
* Candidate data stays in the controlled environment, including AI processing.

Deleting an analysis deletes the PostgreSQL data, candidate results, AI explanations, the ChromaDB collection and embeddings, and any remaining temporary files for that analysis, through the tracked process in Section 11. A periodic sweep also removes orphaned ChromaDB collections that no longer correspond to any analysis.

The MVP is for a controlled environment. It must not be deployed as an unauthenticated public application holding real candidate data. Authentication and secure external deployment must be solved before any external exposure.

Uploaded resumes are untrusted input: validate type and size, never execute them, keep them out of source control, avoid logging candidate data, and keep secrets in environment configuration.

---

## 17. Fairness Testing

Fairness is enforced by the `ScoringProfile` boundary and verified by paired tests.

Each test uses two profiles with identical job-relevant content and different personal information. Changes cover name, gender indicators, pronouns, contact information, institution names, and personal references inserted into free text.

Acceptance rule:

* The scrubbed `job_relevant_text` of both profiles must be identical. Identical text gives identical embeddings, so the semantic score is exactly equal.
* All structured components must be exactly equal.
* Final score, matching evidence, and ranking must be identical.

If the scrubbed texts differ, the test fails. Any undetected personal reference is treated as a fairness defect and fixed in the scrubbing rules.

---

## 18. Evaluation and Testing

The evaluation dataset (about 100 synthetic or anonymized/consented resumes plus multiple job descriptions, labeled by at least two evaluators) is built as the shared early task in Section 3. Results are indicative, not statistically conclusive.

It is used for extraction accuracy, ranking quality, fairness, performance benchmarking, and explanation review. Extraction is benchmarked first. If it fails the target, extraction is improved before building further.

Test levels: unit, service, integration, API, worker, end-to-end, and evaluation.

* **Person 1:** extraction, normalization, section detection, failure cases, extraction benchmark.
* **Person 2:** matching, scoring, ranking, state transitions, finalization, persistence, worker tasks, cleanup, fairness, evaluation infrastructure.
* **Person 3:** API contracts, frontend flows, explanation endpoint, output parsing, grounding validation, explanation UI.

---

## 19. Technology Stack

* **Frontend:** React, Vite, Tailwind CSS
* **Backend:** Python, FastAPI, Pydantic, SQLAlchemy
* **Data:** PostgreSQL, ChromaDB
* **Background execution:** Celery, Redis, multiple worker processes
* **Document processing:** PyPDFLoader, python-docx, rules and regex, spaCy (optional)
* **AI:** Sentence Transformers (`all-MiniLM-L6-v2` initially), Ollama, LangChain where useful
* **Testing:** pytest for unit, integration, and API tests; end-to-end tool to be selected

LangChain is used only for infrastructure such as document loading, embedding, vector-store, and LLM integration. Core logic stays ordinary application code: skill normalization, profile construction, matching, scoring, ranking, fairness controls, and state management.

---

## 20. Errors

Errors are classified as validation, document extraction, duplicate file, requirement, matching, LLM, database, worker, and system errors.

Document-level errors are recorded and the analysis continues. Infrastructure errors, such as PostgreSQL being unavailable, stop the analysis safely.

---

## 21. Deployment

```text
Controlled environment
├── React frontend
└── FastAPI
    ├── PostgreSQL
    ├── ChromaDB
    ├── Redis → Celery workers
    └── Ollama
```

The API and the Celery worker containers share a temporary-storage volume for uploaded files. Docker may be used for reproducible environments. Cloud provider, reverse proxy, authentication, monitoring, and external deployment are decided before any external exposure.

---

## 22. Replaceable Components

These sit behind interfaces: `DocumentLoader`, `EmbeddingService`, `VectorStore`, `LLMService`, and task execution.

---

## 23. Decisions Not Yet Locked

For `API.md`, `DATABASE.md`, or implementation:

* PostgreSQL schema and API request/response schemas
* Embedding model (after benchmarking) and Ollama model
* Score weights
* Extraction algorithms
* Celery worker count, retry settings, and watchdog timing
* Explanation timeout value and temporary-file retention window
* Production infrastructure, authentication, and monitoring

### Initial configuration defaults

Proposed starting values for the team to confirm. All are configurable and are tuned from benchmarks.

* Migration tool: Alembic
* Explanation timeout: 2 minutes
* Temporary-file retention window: 24 hours
* Watchdog and cleanup interval: every 5 minutes
* Resume claim window before re-queue: 10 minutes, adjusted after the first benchmark
* Automatic retries per resume: up to 2 after the initial attempt (3 attempts in total), then the resume becomes `FAILED`
* Automatic retries for finalization errors: up to 2 after the initial attempt (3 attempts in total), then the analysis becomes `FAILED`
* Celery worker count: one worker process per available CPU core to start, tuned by benchmark
* Deletion cleanup: retried on every cleanup interval until it succeeds
* Status polling by the frontend: every 2 seconds while the analysis is `PROCESSING` for the first minute, then every 5 seconds, stopping at `RANKED` or `FAILED`

---

## 24. Locked Constraints

1. React handles presentation; FastAPI handles HTTP; Person 3 owns both plus all LLM work.
2. Person 1 owns document intelligence and all skill normalization.
3. Person 2 owns orchestration, matching, persistence, and the Profile Builder.
4. Person 1 and Person 2 communicate only through frozen shared Pydantic schemas.
5. Only `ScoringProfile` enters the scoring pipeline, and it excludes personal information and institution names.
6. Free-text scrubbing is deterministic, and fairness tests require identical scrubbed text.
7. Job-specific relevance is decided by the matching engine.
8. LLMs never calculate or modify scores.
9. Requirements must be confirmed, and the resume set fixed, before processing starts.
10. Resumes are processed as parallel, idempotent, recoverable background tasks.
11. Duplicates are detected at upload using a content hash with a database constraint.
12. A finalize step ranks once all resumes are in a final state, and is safe to run twice.
13. A failed or needs-review resume never stops the analysis and is never scored.
14. Analysis state ends at `RANKED` or `FAILED`.
15. Explanation state is per candidate, changes atomically, and times out safely.
16. Ranking is available before explanations, which are generated on demand.
17. Every raw file is deleted after its extraction attempt, and orphaned temporary files are cleaned up.
18. Each analysis has isolated vector data, deleted with the analysis.
19. Core matching and scoring logic is deterministic and independently testable.
20. An analysis cannot be deleted while it is `PROCESSING`.
21. Deletion is tracked and retryable: the analysis is hidden at once, vector data and temporary files are deleted before database rows, and orphaned collections are swept.
22. The 50-resume limit counts accepted resumes only and is enforced at the database level, safe under concurrent uploads.
23. Resumes start as `READY`, `DUPLICATE`, or `REJECTED`, and only `READY` resumes are processed.
24. Candidate labels are assigned once after ranking, derived from random candidate IDs, stored, and never recomputed.
25. Temporary files live on a shared volume under generated names.
26. Finalization is one transaction that is safe under concurrent runs. A lost finalization task is recovered by the watchdog, and a finalization failure marks the analysis `FAILED`, which the watchdog never retries.
