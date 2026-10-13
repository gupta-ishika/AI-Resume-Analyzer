# TASKS.md

# Implementation Plan — AI Resume Analyzer & Job Matching System

## 1. Purpose

This document breaks the approved MVP into small, testable tasks for a three-person team.

* `PRD.md` defines product requirements.
* `ARCHITECTURE.md` defines system structure and ownership.
* `API.md` defines endpoint contracts.
* `DATABASE.md` defines persistence and constraints.
* `DESIGN.md` defines UI behavior and visual rules.
* `RULES.md` defines implementation and review rules.
* `TASKS.md` tracks implementation order, dependencies, owners, and acceptance criteria.

If a task conflicts with a source document, stop and resolve the document conflict before implementation. Do not use a task to silently change product scope or architecture.

---

## 2. Team Ownership

Ownership is defined in `ARCHITECTURE.md` Section 3. In summary:

* **Person 1 — Document Intelligence.** JD and resume extraction, text cleaning, section detection, skill extraction and normalization, experience, education, and project extraction, the PII-detection utility, extraction validation and benchmarking, and the test and CI foundation.
* **Person 2 — Matching, Orchestration & Persistence.** Shared integration coordination, Profile Builder, scoring and ranking, embeddings, ChromaDB, PostgreSQL schema and repositories, application services, Celery coordination, state transitions, recovery, cleanup, and matching and fairness evaluation infrastructure.
* **Person 3 — API, Frontend & AI Explanation.** FastAPI routes and request handling, React UI, API contract tests, Ollama integration, prompts, output parsing, grounding validation, the explanation lifecycle, and explanation-quality evaluation. All LLM work belongs to Person 3.

All three people contribute to the early evaluation dataset and review shared contracts. Cross-boundary changes require review by the owning teammate. Person 1 and Person 2 must agree on the shared Pydantic schemas before implementing producer and consumer in parallel.

---

## 3. Task Rules

Every task follows this loop:

```text
Read → Understand → Plan → Implement → Test → Review → Fix → Commit
→ Update documentation if needed
```

* Work in small branches and merge through reviewed pull requests.
* Keep each task independently reviewable.
* Do not begin dependent implementation until its contract or prerequisite is agreed.
* Add tests with meaningful feature changes.
* Do not use real candidate resumes or personal data in tests or in external AI tools.
* Do not commit secrets, raw resumes, temporary files, local databases, or private evaluation data.
* A task is done only when its acceptance criteria pass and the change is reviewed.
* Do not start feature implementation (the DOCINT, DB, MATCH, BG, API, LLM, and UI tasks) until DOC-04 is complete. Phase 1 setup tasks may start after DOC-01.

---

## 4. Phase 0 — Specification Consistency Gate

Goal: make the documents consistent, complete the API schemas, and lock the specification before feature implementation begins.

### DOC-01 — Verify the project documents are consistent

**Owner:** All three; Person 2 coordinates
**Dependencies:** None

The agreed review changes have already been applied to the documents. This task is a team read-through to confirm them.

* Read `PRD.md`, `ARCHITECTURE.md`, `API.md`, `DATABASE.md`, `DESIGN.md`, and `RULES.md` together.
* Confirm that every team member is using the current versions of all six files.
* Check for conflicting lifecycle rules, statuses, endpoints, limits, and ownership.
* Confirm that analysis, resume, and explanation statuses are distinct.
* Confirm the agreed rules: retry after failure but no regeneration after success, shared temporary storage with generated names, enqueue recovery, deletion marker and retry, orphan-vector cleanup, upload concurrency, candidate-label timing, and deletion of uploaded job description files after extraction.
* Record any unresolved decision instead of inventing an answer.
* Confirm or change the initial configuration defaults in `ARCHITECTURE.md` Section 23.

Acceptance criteria:

* No conflicting rules remain across documents.
* Raw-file deletion behavior (resumes and job description files) is consistent everywhere.
* API and database responsibilities are clear enough to implement without guessing.
* All six documents are reviewed by the team.

### DOC-02 — Freeze the shared Pydantic contracts

**Owner:** Person 1 + Person 2; Person 3 reviews API-facing fields and co-owns the explanation output schema
**Dependencies:** DOC-01

Define and agree typed, version-controlled schemas for:

* Extracted job requirements
* Extracted candidate data
* Extraction outcomes and failure categories
* `ScoringProfile`
* `MatchingProfile`
* Match result and evidence
* Validated AI explanation output

Acceptance criteria:

* Required and optional fields are explicit.
* Failure and needs-review outcomes are represented explicitly.
* Canonical skills come from Person 1, and Person 2 does not implement a second synonym layer.
* Producer and consumer tests can use the same schema package.

### DOC-03 — Agree scoring and evaluation protocol

**Owner:** Person 2 leads; all three contribute
**Dependencies:** DOC-01

* Define the evaluation dataset format and annotation process.
* Agree how required and preferred skills, candidate-job relevance, and human shortlists are labeled.
* Define how scoring configurations are versioned and compared.
* Keep exact score weights open until evaluation evidence supports a choice.

Acceptance criteria:

* The evaluation procedure is documented.
* At least two evaluators can label the same examples independently.
* Disagreements can be recorded and resolved.
* No score weights are presented as validated before evaluation.

### API-00 — Draft field-level API schemas

**Owner:** Person 3 drafts; Person 2 reviews
**Dependencies:** DOC-02

* Review, correct, and finalize the proposed field-level schemas in `API.md` Section 6, which are drafted in advance so the frontend can prepare.
* Cover the per-file upload result (status and reason code), the list-resumes response, status counts and their meanings, analysis summary and list, requirements, candidate list, candidate detail (four blocks), explanation request and response, and the shared error response with its initial code list.
* Confirm the status polling default from `ARCHITECTURE.md` Section 23.

Acceptance criteria:

* `API.md` Section 6 is final: the "Proposed" marking is removed once the types match the frozen DOC-02 contracts.
* The frontend and backend can work against the same fields and types.
* Types match the shared schemas from DOC-02.
* Person 2 has reviewed the schemas.

### DOC-04 — Approve and lock the specification

**Owner:** All three; Person 2 coordinates
**Dependencies:** DOC-01, DOC-02, DOC-03, API-00

* Read all six documents once more after the API schemas are added.
* Confirm that no contract-level decision is left undefined. Parameters that are open by design, such as score weights, stay open.
* Approve the documents and record the approved version.

Acceptance criteria:

* All six documents are approved by all three people.
* Later changes follow `RULES.md` Section 25.
* Phase 0 is complete only when this task is done, not merely because the documents were edited.

---

## 5. Phase 1 — Repository and Development Foundation

### SET-01 — Establish repository structure and team workflow

**Owner:** All three; Person 2 coordinates
**Dependencies:** DOC-01

* Agree the repository layout for frontend, backend, shared schemas, tests, and documentation.
* Set up feature branches and pull-request review.
* Add a root README with setup instructions and links to the project documents.
* Add `.gitignore` entries for secrets, uploaded files, local databases, vector data, caches, and build artifacts.

Acceptance criteria:

* All team members can clone the repository and understand its layout.
* No secrets or candidate data are tracked.
* Pull-request review expectations are documented.

### SET-02 — Establish backend environment

**Owner:** Person 2
**Dependencies:** SET-01

* Set up the Python environment and dependency management.
* Add the FastAPI entry point and configuration loading, plus a `.env.example` with placeholder values only.
* Add SQLAlchemy and PostgreSQL connection configuration.
* Add structured, privacy-safe logging and central error handling foundations.

Acceptance criteria:

* The backend starts locally.
* Configuration comes from environment variables.
* Missing required configuration fails clearly without printing secrets.
* A basic health endpoint works.

### SET-03 — Establish frontend environment

**Owner:** Person 3
**Dependencies:** SET-01

* Set up React, Vite, and Tailwind CSS.
* Establish routing, shared layout, typography, colors, and reusable UI primitives from `DESIGN.md`.
* Add environment-based API base URL configuration.

Acceptance criteria:

* The frontend starts locally.
* Shared layout and initial navigation render correctly.
* No matching or scoring logic exists in the frontend.

### SET-04 — Establish local service environment

**Owner:** Person 2; Person 3 validates Ollama integration needs
**Dependencies:** SET-02

* Set up PostgreSQL, Redis, ChromaDB, and Ollama for the controlled development environment.
* Configure the Celery worker and separate resume-processing and explanation queues.
* Define the shared temporary volume accessible to API and worker containers.
* Use generated temporary storage names. Never use original filenames as storage paths.

Acceptance criteria:

* Required services can be started and stopped reproducibly.
* The API and worker can access the same temporary volume.
* No uploaded file is stored in source control.
* Service configuration is documented without secrets.

### SET-05 — Establish test and CI foundations

**Owner:** Person 1
**Dependencies:** SET-02

* Configure pytest and test settings.
* Add shared test fixtures and conventions, with synthetic data only.
* Add a minimal CI check for linting, type checks where agreed, and automated tests.

Acceptance criteria:

* Tests run locally and in CI with documented commands.
* Tests do not depend on real candidate data.
* Person 3 can add API test conventions on top of the same setup.

### SET-06 — Establish migration and test database foundations

**Owner:** Person 2
**Dependencies:** SET-02, SET-04, SET-05

* Configure the migration tool (default: Alembic, since the stack uses SQLAlchemy).
* Establish an isolated test database and test configuration.

Acceptance criteria:

* Database schema changes are versioned through migrations.
* Tests run against an isolated database.

---

## 6. Phase 2 — Evaluation Dataset and Extraction Baseline

### DATA-01 — Build the seed evaluation set

**Owner:** All three; Person 1 leads extraction annotations
**Dependencies:** DOC-03

* Create about 10 to 15 synthetic, properly anonymized, or consented resumes and a few job descriptions.
* Cover varied layouts, skill synonyms, missing fields, duplicate content, corrupted files, and scanned or image-only PDFs.
* Label relevant skills and requirement types using the agreed format.

This seed set unblocks extraction and scoring work while the full dataset is built.

Acceptance criteria:

* The set contains no unconsented real candidate data.
* Labels are stored in the documented format.
* It is enough to develop and test extraction and scoring logic.

### DATA-02 — Build the full evaluation dataset

**Owner:** All three; Person 1 leads extraction annotations
**Dependencies:** DATA-01

* Grow the dataset to approximately 100 synthetic, properly anonymized, or consented resumes with multiple representative job descriptions.
* Include difficult extraction cases and duplicate content.
* Have at least two evaluators independently label relevant skills, requirement types, candidate-job relevance, and the human shortlist.

Acceptance criteria:

* The dataset contains no unconsented real candidate data.
* Labels and evaluator disagreements are stored in a documented format.
* It can be reused for extraction, ranking, fairness, and explanation evaluation.
* Access to any consented data is controlled.

### DOCINT-01 — Implement PDF/DOCX extraction

**Owner:** Person 1
**Dependencies:** DOC-02, SET-02, DATA-01

* Implement text extraction for supported PDF and DOCX files.
* Detect empty, corrupted, unsupported, scanned or image-only, and unreliable-layout documents.
* Return typed extraction outcomes rather than ambiguous empty objects.
* Do not introduce LLM-based extraction into the MVP.

Acceptance criteria:

* Unit tests cover supported and failed document cases.
* Scanned or image-only files without reliably extractable text are not treated as valid low-quality candidates.
* Failure categories and user-safe reasons are explicit.

### DOCINT-02 — Implement cleaning and section detection

**Owner:** Person 1
**Dependencies:** DOCINT-01

* Clean extracted text without destroying relevant content.
* Identify sections such as skills, experience, projects, and education.
* Preserve the source evidence needed to support extracted structured fields.

Acceptance criteria:

* Section detection is tested against the evaluation data.
* Missing or ambiguous sections are represented honestly.
* Raw resume text is not exposed through application responses or logs.

### DOCINT-03 — Implement skill extraction and normalization

**Owner:** Person 1
**Dependencies:** DOCINT-02, DOC-02

* Extract skills from resumes and job descriptions.
* Normalize equivalent names to canonical skills, including agreed synonym cases.
* Keep required and preferred job skills distinct.
* Maintain one normalization implementation, owned by Person 1.

Acceptance criteria:

* Synonym and false-positive tests pass.
* Canonical skill output conforms to the shared schema.
* Person 2 and Person 3 consume normalized skills instead of implementing competing synonym logic.

### DOCINT-04 — Implement experience, education, and project extraction

**Owner:** Person 1
**Dependencies:** DOCINT-02, DOC-02

* Extract structured experience, responsibilities, projects, and education.
* Preserve evidence and uncertainty where available.
* Do not infer missing qualifications or dates.

Acceptance criteria:

* Output conforms to the shared Pydantic schemas.
* Missing information is distinguishable from a confirmed absence.
* Tests cover incomplete and unusual resumes.

### DOCINT-05 — Implement JD requirement extraction

**Owner:** Person 1
**Dependencies:** DOCINT-03, DOC-02

* Extract required skills, preferred skills, experience requirements, education requirements, and other explicit requirements.
* Extract the job-relevant text used for semantic matching.
* Report when requirements are insufficient or uncertain.
* Support recruiter review and manual correction through structured output.

Acceptance criteria:

* Required and preferred requirements remain distinct.
* Uncertain extraction does not silently become a confirmed requirement.
* The output supports the requirement-review screen.

### DOCINT-06 — Implement extraction validation and benchmark

**Owner:** Person 1
**Dependencies:** DOCINT-01 through DOCINT-05, DATA-02

* Evaluate extraction precision and recall against labeled data.
* Analyze common failures and improve rules and section handling.
* Record results and known limitations.

Acceptance criteria:

* Metrics are reproducible.
* PRD extraction targets are reported honestly.
* If targets are missed, improvement work is recorded before dependent features assume the target is met.

---

## 7. Phase 3 — Persistence and Shared Domain Foundations

### DB-01 — Implement database schema and migrations

**Owner:** Person 2
**Dependencies:** DOC-01, DOC-02, SET-06

* Implement `Analysis`, `JobRequirements`, `Resume`, `Candidate`, `MatchResult`, and `Explanation` persistence per `DATABASE.md`.
* Use relational fields for identity, lifecycle, timestamps, and queryable state.
* Use JSONB only for validated evolving structured payloads.
* Add foreign keys, status constraints, one-requirements-per-analysis, one-match-result-per-candidate, one-explanation-per-candidate, unique rank and label, the deletion marker, and the required indexes.
* Enforce the canonical content-hash uniqueness invariant per analysis.

Acceptance criteria:

* Migrations create the agreed schema from an empty database.
* Constraints are exercised by tests.
* Duplicate and candidate or result uniqueness are enforced by the database, not only application checks.

### DB-02 — Implement repositories and transaction boundaries

**Owner:** Person 2
**Dependencies:** DB-01

* Add repositories for analyses, requirements, resumes, candidates, results, and explanations.
* Define transaction boundaries for state changes and finalization.
* Use conditional updates for state transitions.
* Ensure database access does not leak into route handlers.

Acceptance criteria:

* Repository tests cover expected success and conflict cases.
* Concurrent state changes cannot both succeed when only one transition is permitted.
* Application services use repositories rather than ad hoc SQL.

### DB-03 — Implement analysis and requirements services

**Owner:** Person 2
**Dependencies:** DB-02, DOCINT-05

* Create analyses and persist extracted JD requirements.
* Support requirement review and edits while `REQUIREMENTS_PENDING`.
* Validate sufficient requirements before starting.
* Prevent requirement edits after processing starts.

Acceptance criteria:

* Requirement changes are persisted and validated.
* Invalid state changes return a typed conflict.
* The analysis lifecycle follows the architecture.

### DB-04 — Implement resume registration and upload-limit protection

**Owner:** Person 2; Person 3 integrates the upload endpoint
**Dependencies:** DB-02

* Persist per-file upload outcomes without storing rejected file contents.
* Enforce the maximum of 50 accepted resumes across concurrent upload requests.
* Exclude duplicates and rejected files from the accepted-resume count.
* Default mechanism: lock the analysis row in the same transaction that counts and registers accepted resumes. Use another proven mechanism only if the team agrees and documents it.
* Store canonical and duplicate relationships correctly.

Acceptance criteria:

* Concurrent requests cannot exceed the accepted-resume limit.
* Identical content cannot create two canonical resumes in one analysis.
* Duplicates do not create candidate records or processing tasks.
* Upload outcomes can be revisited in saved analyses.

---

## 8. Phase 4 — Profile Builder, Matching, and Ranking

### MATCH-01 — Implement shared PII-detection utility

**Owner:** Person 1
**Dependencies:** DOC-02, DOCINT-02

* Detect extracted names, emails, phone numbers, institution names, and other supported personal identifiers.
* Support deterministic scrubbing of approved professional text.
* Define known limitations and test cases.

Acceptance criteria:

* The utility is deterministic and independently tested.
* Tests cover repeated occurrences and identifiers embedded in free text.
* It returns safe structured results for Person 2 to integrate.

### MATCH-02 — Implement Profile Builder

**Owner:** Person 2
**Dependencies:** MATCH-01, DOCINT-02 through DOCINT-04, DOC-02

* Construct `ScoringProfile` only from approved structured fields and professional sections.
* Remove the extracted name, email, phone, institution names, detected identifiers, and gendered references according to the architecture.
* Never concatenate the raw resume.
* Keep candidate display identity separate from scoring data.

Acceptance criteria:

* Matching interfaces accept `ScoringProfile`, not the full candidate object.
* Tests prove identity fields do not enter the scoring profile.
* Paired fairness tests verify identical scrubbed text for equivalent job-relevant content.

### MATCH-03 — Implement MatchingProfile construction

**Owner:** Person 2
**Dependencies:** DB-03, DOCINT-05

* Build the matching view from recruiter-confirmed requirements.
* Keep required skills, preferred skills, experience, education, explicit requirements, and job-relevant JD text separate.
* Represent unspecified requirements explicitly.

Acceptance criteria:

* Only confirmed requirements are used for ranking.
* Unspecified requirements are not treated as failed requirements.
* Tests cover empty and partially specified requirement groups.

### MATCH-04 — Implement embedding service and ChromaDB adapter

**Owner:** Person 2
**Dependencies:** SET-04, MATCH-02, MATCH-03

* Place embedding and vector-store access behind interfaces.
* Benchmark the initial `all-MiniLM-L6-v2` candidate for ranking quality, latency, and memory.
* Create analysis-specific vector collections.
* Ensure semantic matching uses safe profile text and matching-profile text, never raw resumes.

Acceptance criteria:

* Embedding and vector operations are independently testable.
* No cross-analysis retrieval occurs.
* Collection creation and cleanup are idempotent.
* The model and configuration version is recorded as required by the scoring configuration.

### MATCH-05 — Implement deterministic scoring engine

**Owner:** Person 2
**Dependencies:** MATCH-02, MATCH-03, MATCH-04, DATA-01, DOC-03

* Calculate required-skill coverage, preferred-skill coverage, semantic relevance, relevant experience, and applicable education and explicit requirements.
* Keep scoring independent of any LLM.
* Store weights and thresholds in versioned configuration.
* Make unspecified or indeterminable components explicit.

Acceptance criteria:

* The same inputs and scoring configuration produce the same component and final scores.
* The score breakdown is available for the UI.
* No personal identity fields enter scoring.
* No LLM call is required to calculate a score.

### MATCH-06 — Implement deterministic ranking and candidate labels

**Owner:** Person 2
**Dependencies:** MATCH-05, DB-02

* Rank candidates by final score and the agreed tie-breakers.
* Assign candidate display labels only after ranking finishes.
* Derive labels from random system-generated candidate IDs, persist them, and never recompute them.
* Keep the label field empty before assignment.
* Use sequential, zero-padded labels (for example `Candidate 01`), ordered by candidate ID.
* Assign labels inside the finalization transaction and only to candidates that have no label yet.
* Enforce label uniqueness within an analysis once assigned.

Acceptance criteria:

* Ranking and tie-breaking are deterministic.
* Labels do not depend on names, filenames, upload order, or rank order.
* Labels remain unchanged when a saved analysis is reopened.
* Running finalization twice leaves every label unchanged.
* Two finalization attempts run concurrently leave consistent ranks and labels.
* Failed and needs-review resumes never receive a candidate score or rank.

### MATCH-07 — Implement matching and fairness evaluation

**Owner:** Person 2; Person 1 supports extraction and profile cases
**Dependencies:** MATCH-02 through MATCH-06, DATA-02

* Evaluate the extraction-to-ranking flow against labeled data.
* Test pairs with identical job-relevant qualifications but different personal attributes.
* Measure top-five overlap with human shortlists.
* Tune and document scoring weights based on evidence.

Acceptance criteria:

* Fairness tests require identical scrubbed text, structured components, score, evidence, and ranking.
* PRD quality metrics are reported with limitations.
* Weight changes are versioned and results are reproducible.

---

## 9. Phase 5 — Background Processing and Recovery

### BG-01 — Implement Celery task infrastructure

**Owner:** Person 2
**Dependencies:** SET-04, DB-02

* Configure the resume-processing and explanation queues.
* Configure worker processes, retries, task timeouts, and privacy-safe task logging.
* Define idempotency keys using `analysis_id` and `resume_id` for resume processing.

Acceptance criteria:

* Workers can process tasks independently of API requests.
* A worker restart does not permanently lose recoverable work.
* Queue failures are observable without logging candidate content.

### BG-02 — Implement raw-file lifecycle and cleanup

**Owner:** Person 2; Person 3 integrates temporary upload storage
**Dependencies:** SET-04, DB-04, DOCINT-01

* Store files on the shared temporary volume using generated names.
* Ensure the API and worker containers can access the same stored object.
* Delete duplicate files immediately after duplicate detection.
* Never retain files rejected at upload.
* Delete every accepted raw resume after its extraction attempt, regardless of outcome.
* Delete an uploaded JD file after requirement extraction, regardless of outcome.
* Add startup and periodic cleanup for stale or orphaned temporary files.
* In a `REQUIREMENTS_PENDING` analysis, delete files that pass the retention window and mark their resumes `REJECTED` with reason `UPLOAD_EXPIRED`.

Acceptance criteria:

* Original filenames are never used as storage paths.
* Raw files are removed after extraction attempts for success and all failure cases.
* Crash simulation demonstrates that orphaned files are eventually removed.
* Expired uploads in a pending analysis are removed and shown to the recruiter as expired.
* Raw resume text and files do not enter logs or downstream matching.

### BG-03 — Implement per-resume processing task

**Owner:** Person 2 integrates Person 1's extraction contract
**Dependencies:** DOCINT-01 through DOCINT-05, MATCH-02 through MATCH-05, BG-01, BG-02

* Claim the resume with a conditional update from `READY` to `PROCESSING`, recording a start time. If the claim fails, another worker already owns it, so exit without processing.
* Validate the resume record and state.
* Run extraction and create canonical structured data.
* Build the safe scoring profile.
* Generate embeddings and compute matching data.
* Persist successful results or a typed failed or needs-review outcome.
* Delete the raw file in a guaranteed cleanup path.

Acceptance criteria:

* Tasks are idempotent and retryable.
* A resume cannot be processed by two workers at once.
* One failed resume does not stop other resumes.
* No failed or needs-review resume receives a score.
* Raw-file deletion happens regardless of extraction outcome.

### BG-04 — Implement Start Analysis and safe enqueue/recovery

**Owner:** Person 2; Person 3 owns the API route
**Dependencies:** DB-03, DB-04, BG-01, BG-03

* Use a conditional transition from `REQUIREMENTS_PENDING` to `PROCESSING`.
* Fix the accepted resume set at start.
* Enqueue one task per accepted `READY` resume.
* Make repeated start requests return a conflict without enqueuing duplicate work.
* Ensure enqueue failure after the state change is recoverable by a watchdog.

Acceptance criteria:

* The API returns promptly and does not wait for processing to finish.
* A second start request cannot initiate a second run.
* Redis or queue unavailability does not leave resumes permanently unprocessed.
* Watchdog recovery safely re-queues unfinished resumes.

### BG-05 — Implement finalization and watchdog

**Owner:** Person 2
**Dependencies:** BG-03, BG-04, MATCH-06

* Detect when all accepted resumes reach final statuses.
* Run finalization as one transaction: lock the analysis row, exit if the status is not `PROCESSING`, write ranks and labels, set `RANKED`, and commit.
* Retry transient finalization errors with backoff (up to 2 retries after the initial attempt, 3 attempts in total). On other errors or exhausted retries, mark the analysis `FAILED` with reason `FINALIZATION_FAILED`.
* Recover undelivered finalization tasks and lost workers through the watchdog without counting them as failed attempts. Never re-enqueue finalization for a `FAILED` analysis.
* If every resume fails, produce an empty ranking and failure list while the analysis still reaches `RANKED`.
* Re-queue `READY` resumes of a `PROCESSING` analysis that were never claimed within the claim window.
* Reset stale `PROCESSING` resumes (past the window) to `READY` for a limited number of retries, then mark them `FAILED`.
* Detect analyses that remain `PROCESSING` after every accepted resume reached a final status (lost finalization) and enqueue finalization again.
* Detect analyses stuck in `PROCESSING` and recover them, or mark them `FAILED` when recovery is impossible.
* Detect stale explanation tasks once explanation support is integrated.

Acceptance criteria:

* Finalization is safe to execute more than once and concurrently.
* Two concurrent finalizations leave consistent ranks and labels.
* A finalization failure marks the analysis `FAILED` with no partial ranking.
* A document-level failure does not fail the whole analysis.
* Analysis state does not remain `PROCESSING` indefinitely under recoverable conditions.
* Recovery decisions are logged without sensitive candidate data.
* A resume is never processed twice concurrently, and automatic retries are limited.
* A lost finalization task is recovered without duplicating results or changing labels.

### BG-06 — Implement analysis deletion and vector cleanup

**Owner:** Person 2; Person 3 owns API and UI integration
**Dependencies:** DB-02, MATCH-04, BG-01

* Allow deletion from `REQUIREMENTS_PENDING`, `RANKED`, and `FAILED`, and reject it while processing.
* Treat a repeated delete after the marker is set as not found, with no change to state.
* Mark deletion in progress without adding a new analysis lifecycle state.
* Hide marked analyses from normal list and get responses.
* Retry ChromaDB collection deletion safely, then remove associated database rows.
* Add a periodic sweep for orphaned ChromaDB collections and remaining temporary files.

Acceptance criteria:

* Repeated deletion attempts are safe.
* A failed vector deletion remains tracked and retryable.
* Successful deletion removes all associated PostgreSQL records and vector data.
* Orphaned collections are eventually detected and removed.

---

## 10. Phase 6 — API Implementation

### API-01 — Implement shared API schemas and errors

**Owner:** Person 3
**Dependencies:** DOC-01, DOC-02, API-00, DB-01

* Implement Pydantic request and response schemas from `API.md`.
* Implement the stable error response with category, code, and user-safe message.
* Map validation, state conflict, not-found, file, extraction, worker, LLM, database, and system errors consistently.

Acceptance criteria:

* API response fields match the contract.
* Errors never expose stack traces, secrets, database errors, or internal paths.
* The frontend can branch on stable error codes.

### API-02 — Implement analysis and requirement endpoints

**Owner:** Person 3
**Dependencies:** API-01, DB-03, DOCINT-05, BG-02

* Implement create analysis with an uploaded or pasted JD.
* Delete an uploaded JD file after requirement extraction, regardless of outcome.
* Implement list and get analysis and get and edit requirements.
* Use the `page` and `limit` pagination convention.
* Enforce requirement-state restrictions.

Acceptance criteria:

* Endpoints use application services, not business logic in routes.
* JD extraction results and manual-review indicators are returned consistently.
* State conflicts use the documented error format.
* No uploaded JD file remains after the request ends.

### API-03 — Implement resume upload endpoint

**Owner:** Person 3
**Dependencies:** API-01, DB-04, BG-02

* Accept one or more files per multipart request.
* Validate type, size, and batch limits.
* Compute content hashes and return per-file upload outcomes.
* Write files to shared temporary storage under generated names.
* Support frontend small-batch uploads for per-file progress.
* Implement the list-resumes endpoint so a reopened pending analysis shows each uploaded file with its status and reason.

Acceptance criteria:

* Each submitted file has a clear outcome and reason.
* A reopened pending analysis lists every uploaded file, including expired ones, with status and reason.
* The accepted-resume count is protected across concurrent requests.
* Duplicates and rejected files are reported but never queued.
* No original filename is used as a storage path.

### API-04 — Implement Start Analysis and status endpoints

**Owner:** Person 3
**Dependencies:** API-01, BG-04, BG-05

* Implement the explicit start endpoint.
* Implement the status endpoint with analyzed-resume counts and separately reported duplicates and rejections.
* Return promptly after a successful state transition and scheduling.
* Document polling behavior.

Acceptance criteria:

* A second start returns a conflict.
* Counts have consistent meanings and do not double-count duplicates.
* Status remains useful during partial failure and recovery.

### API-05 — Implement candidate list and detail endpoints

**Owner:** Person 3
**Dependencies:** API-01, MATCH-06, DB-02

* Return ranked candidates using stable display labels.
* Include score summaries and required-skill coverage.
* Return failed and needs-review files separately.
* Return candidate identity, extracted structured data, matching evidence, and explanation state as separate response blocks.

Acceptance criteria:

* Ranking responses never include names or contact details.
* Candidate detail never includes raw resume text or raw file access.
* Failed and needs-review resumes never appear as ranked candidates.
* Unspecified requirements are represented as `not_specified`.

### API-06 — Implement deletion endpoint

**Owner:** Person 3
**Dependencies:** API-01, BG-06

* Implement the deletion request with safe conflict handling.
* Return `202` after the analysis is marked for deletion, per `API.md`.
* Ensure marked analyses are hidden immediately and return not found.

Acceptance criteria:

* Deletion while processing returns a conflict.
* A repeated delete after the marker is set returns `404` and changes nothing.
* Deletion from a pending analysis works.
* Partial vector-cleanup failures remain recoverable in the background.
* API responses never claim cleanup is complete while it is still pending.

---

## 11. Phase 7 — AI Explanation

### LLM-01 — Define explanation schema and grounding rules

**Owner:** Person 3
**Dependencies:** DOC-02, MATCH-05

* Define the validated explanation structure: strengths, gaps, experience alignment, and assessment.
* Define grounding checks against matching evidence and structured data.
* Ensure unnecessary identity data is excluded from LLM context.

Acceptance criteria:

* Explanation output is schema-validated.
* Unsupported qualifications or achievements are rejected or corrected through a bounded validation flow.
* The explanation schema is version-controlled.

### LLM-02 — Implement Ollama service adapter

**Owner:** Person 3
**Dependencies:** SET-04, LLM-01

* Implement Ollama integration behind the `LLMService` abstraction.
* Benchmark candidate local models for latency, hardware needs, explanation quality, and structured-output reliability.
* Keep the chosen model configurable.

Acceptance criteria:

* The LLM can be substituted behind the interface.
* Failures and timeouts are explicit.
* No scoring or ranking code calls the LLM.

### LLM-03 — Implement explanation request lifecycle

**Owner:** Person 3; Person 2 supports persistence and worker integration
**Dependencies:** DB-02, BG-01, LLM-01, LLM-02

* Implement the atomic transition from `NOT_REQUESTED` or `FAILED` to `GENERATING`.
* Run explanation work on its separate queue.
* Return the existing state without enqueuing when already `GENERATING` or `READY`.
* Persist only validated output.
* Mark failed or timed-out jobs as `FAILED`.

Acceptance criteria:

* Concurrent requests cannot enqueue duplicate explanation jobs.
* Retry after `FAILED` is allowed.
* Regeneration after `READY` is not supported in the MVP.
* Failed explanations never affect score or rank.

### LLM-04 — Implement explanation endpoint and quality evaluation

**Owner:** Person 3
**Dependencies:** API-01, LLM-03, DATA-02

* Implement the request and get explanation endpoints.
* Evaluate factual grounding, unsupported claims, clarity, and usefulness against the evaluation dataset.
* Record model and configuration versions for reproducibility where required.

Acceptance criteria:

* The UI can poll or refresh explanation state.
* Only validated explanations are displayed.
* Explanation failure leaves matching results available.
* Quality findings and known limitations are documented.

---

## 12. Phase 8 — Frontend Implementation

### UI-01 — Implement application shell and dashboard

**Owner:** Person 3
**Dependencies:** SET-03, API-02

* Implement navigation, the dashboard, the saved analyses list, and the create-analysis entry point.
* Follow the layout, color, typography, and reusable component rules in `DESIGN.md`.
* Reopen a saved analysis at the right step: Pending at requirements or upload, Processing at the processing screen, Ranked at results, and Failed at an error screen.

Acceptance criteria:

* Empty, loading, error, and populated dashboard states exist.
* Saved analyses can be opened and resume at the correct step.
* The responsive layout works at the specified viewport sizes.

### UI-02 — Implement JD input and requirement review

**Owner:** Person 3
**Dependencies:** API-02

* Implement JD file upload and paste.
* Display extracted requirements with manual editing.
* Clearly indicate insufficient requirements and prevent confirmation until sufficient criteria exist.

Acceptance criteria:

* Required and preferred groups remain distinct.
* Edits persist through the API.
* Requirements must be confirmed before resume processing.

### UI-03 — Implement resume upload and per-file progress

**Owner:** Person 3
**Dependencies:** API-03

* Implement multi-file selection and drag and drop.
* Send small batches to support per-file progress.
* Display ready, duplicate, unsupported, oversized, limit-reached, expired, and rejected outcomes. An expired file prompts the recruiter to upload it again.
* Provide frontend affordances for the overall accepted-resume limit while relying on backend enforcement as the source of truth.

Acceptance criteria:

* Each file has a visible status and actionable reason.
* Duplicate and rejected files are not presented as accepted resumes.
* Start Analysis is enabled only when requirements are confirmed and at least one accepted resume is ready.
* Uploads are locked after start.

### UI-04 — Implement processing screen

**Owner:** Person 3
**Dependencies:** API-04

* Display processing progress, completed, failed, needs-review, remaining, and duplicate or rejection counts separately.
* Poll according to the agreed API behavior.
* Handle interrupted requests and reloads.

Acceptance criteria:

* Counts use the same definitions as `API.md`.
* Failed and needs-review files have reasons.
* The screen never presents failed files as low-scoring candidates.

### UI-05 — Implement ranked results and candidate details

**Owner:** Person 3
**Dependencies:** API-05

* Display the ranking table using system-generated labels.
* Display the score breakdown and evidence.
* Show failed and needs-review files in separate sections.
* Show identity only on the candidate detail screen.

Acceptance criteria:

* Ranking appears without waiting for AI explanations.
* Score factors and unspecified requirements are explained clearly.
* The interface does not present a score as a hiring decision.

### UI-06 — Implement AI explanation UI

**Owner:** Person 3
**Dependencies:** LLM-04

* Implement the `NOT_REQUESTED`, `GENERATING`, `READY`, and `FAILED` states.
* Allow retry after failure.
* Do not provide regeneration after a successful explanation.
* Keep the explanation visually secondary to matching evidence.
* Keep the generating state when the recruiter leaves and returns.

Acceptance criteria:

* Duplicate requests are prevented in the UI and backend.
* Explanation failure does not hide or change matching results.
* Explanations are clearly labeled AI-generated.

### UI-07 — Implement saved-analysis deletion

**Owner:** Person 3
**Dependencies:** API-06

* Implement the delete confirmation dialog.
* Offer deletion for Pending, Ranked, and Failed analyses. Disable it while an analysis is processing, with a short explanation.
* After the recruiter confirms, remove the analysis from the list immediately.
* Do not show a deletion-in-progress state. Cleanup continues in the background.

Acceptance criteria:

* The user cannot delete without confirmation.
* A deleted analysis disappears from the list at once and cannot be opened.
* Failed background cleanup is retried by the system without making the analysis visible again.

---

## 13. Phase 9 — Integration and End-to-End Testing

### TEST-01 — Test shared contracts and ownership boundaries

**Owner:** All three
**Dependencies:** DOC-02 and the first integrated modules

* Test producer and consumer compatibility for the shared Pydantic schemas.
* Verify Person 2 does not duplicate Person 1's skill normalization.
* Verify matching receives only `ScoringProfile`.
* Verify Person 3's LLM path cannot modify scores.

Acceptance criteria:

* Contract tests run in CI or the documented test workflow.
* Breaking contract changes fail tests clearly.

### TEST-02 — Test concurrent uploads and state transitions

**Owner:** Person 2 + Person 3
**Dependencies:** DB-04, API-03, BG-04

* Test concurrent upload requests near the 50 accepted-resume limit.
* Test concurrent duplicate uploads.
* Test double-click or repeated Start Analysis.
* Test edits and uploads after start, and deletion while processing.
* Test deletion from a pending analysis and repeated delete requests.

Acceptance criteria:

* Limits and state rules hold under concurrent requests.
* No duplicate canonical resume or duplicate processing run is created.

### TEST-03 — Test background failures and recovery

**Owner:** Person 2; Person 3 tests visible API behavior
**Dependencies:** BG-02 through BG-06, API-04, API-06

* Simulate worker crashes, Redis unavailability during enqueue, extraction failures, and interrupted processing.
* Verify the watchdog re-queues unfinished resumes.
* Verify finalization can run repeatedly.
* Verify raw-file and vector cleanup recovery.
* Simulate a lost or failed finalization task after every resume reaches a final status, and verify the watchdog triggers finalization again.
* Verify the analysis reaches `RANKED` and that scores, ranks, and candidate labels are neither duplicated nor changed.
* Run two finalization attempts concurrently and verify ranks and labels are consistent and the analysis ends `RANKED` once.
* Simulate repeated finalization errors and verify the analysis becomes `FAILED` with `FINALIZATION_FAILED`, with no partial ranking and no further watchdog re-enqueue.
* Verify expired uploads in a pending analysis are deleted and shown as expired.

Acceptance criteria:

* No recoverable analysis remains stuck indefinitely.
* A lost finalization task is recovered with no duplicate or changed results.
* Concurrent finalization is consistent, and a failing finalization ends `FAILED` without a partial result.
* No raw file remains indefinitely after an interrupted attempt.
* Vector deletion failures remain tracked and are retried.

### TEST-04 — Test privacy and fairness end to end

**Owner:** Person 2 leads; Person 1 and Person 3 contribute
**Dependencies:** MATCH-07, API-05, LLM-04

* Verify identity information does not affect scores.
* Verify names and contact details are absent from ranking API responses.
* Verify raw resume text is absent from UI, API responses, and logs.
* Verify LLM context excludes unnecessary identifying information.

Acceptance criteria:

* Paired fairness tests pass.
* API and UI privacy tests pass.
* Any failure is treated as a release blocker.

### TEST-05 — Run end-to-end acceptance scenarios

**Owner:** All three
**Dependencies:** UI-01 through UI-07, TEST-01 through TEST-04

Cover at least:

1. Valid JD, manual requirement edits, valid resumes, ranked results.
2. Insufficient JD requirements and manual correction.
3. Mixed valid, failed, duplicate, and needs-review resumes.
4. All resumes fail, resulting in an empty ranking and failure list.
5. Request explanation, explanation failure, and retry.
6. Reopen a saved analysis and confirm stable labels and results.
7. Delete a ranked analysis and verify database and vector cleanup.
8. Worker or queue failure followed by successful recovery.

Acceptance criteria:

* All required user flows work through the UI and API.
* Errors are actionable and do not expose internals.
* Results persist as specified.
* Deletion and privacy requirements hold.

---

## 14. Phase 10 — Performance, Security, and Release Readiness

### REL-01 — Benchmark performance targets

**Owner:** Person 2 leads; Person 1 and Person 3 optimize their components
**Dependencies:** TEST-05, MATCH-07

* Benchmark 20-resume and 50-resume analyses on a documented reference environment.
* Benchmark explanation latency separately.
* Record worker count, model versions, hardware, and dataset details.
* Tune only with measured evidence.

Acceptance criteria:

* Report whether the PRD targets are met: up to 20 resumes in 60 seconds, up to 50 in 150 seconds, and an individual explanation in 15 seconds.
* Any unmet target has a documented cause and mitigation plan.
* Do not claim targets are met without measurements.

### REL-02 — Security and privacy review

**Owner:** All three; Person 2 coordinates
**Dependencies:** TEST-04

* Review upload validation, temporary storage, file deletion, logs, secrets, API errors, database access, and network exposure.
* Verify the application is not publicly exposed with real candidate data without authentication and secure deployment controls.
* Check dependencies and configuration.

Acceptance criteria:

* No known critical privacy or security defect remains open.
* Secrets and private candidate data are absent from the repository.
* Deployment constraints are documented.

### REL-03 — Documentation and handover

**Owner:** All three
**Dependencies:** REL-01, REL-02

* Update the README with setup, architecture overview, API usage, environment configuration, migrations, worker startup, tests, and known limitations.
* Document evaluation and performance results.
* Ensure all team members can explain the flow and their owned modules.

Acceptance criteria:

* A new team member can set up the controlled environment using the documentation.
* Tests and migrations run with documented commands.
* Known limitations are explicit.
* All deliverables are reviewed and committed.

---

## 15. Dependency Overview

```text
Specification consistency (DOC-01)
        ↓
Shared Pydantic contracts + evaluation protocol (DOC-02, DOC-03)
        ↓
Field-level API schemas (API-00) and specification lock (DOC-04)
        ↓
Repository and service foundations (SET)  +  Seed evaluation set (DATA-01)
        ↓
Extraction baseline ───────────────┐
        ↓                          │
Profile Builder + matching         │
        ↓                          │
Background processing + recovery   │
        ↓                          │
API contracts and endpoints        │
        ↓                          │
Frontend integration + explanation │
        └──────────────┬───────────┘
                       ↓
        Full dataset (DATA-02) → extraction benchmark, tuning,
        explanation evaluation
                       ↓
            End-to-end and fairness tests
                       ↓
            Performance and security review
                       ↓
                    Release
```

Tasks within a phase may run in parallel only when their dependencies and shared contracts are satisfied. Person 1 and Person 2 must not implement competing versions of shared extraction schemas or skill normalization.

---

## 16. MVP Release Gates

Do not consider the MVP ready until all of the following are true:

* Project documents and shared schemas are consistent.
* JD requirements can be reviewed and confirmed before processing.
* Multiple PDF and DOCX resumes can be uploaded with per-file outcomes.
* The accepted-resume limit and duplicate detection are concurrency-safe.
* Raw resume files and uploaded JD files are deleted after their extraction attempts, and orphaned files are cleaned up.
* Valid resumes process independently through background workers.
* Failed and needs-review resumes are never scored or ranked.
* Matching uses only `ScoringProfile`.
* Scoring and ranking are deterministic, explainable, and independent of the LLM.
* Candidate labels are stable and persisted after ranking.
* Results appear before optional AI explanations.
* Explanation retries after failure work without duplicate jobs or successful regeneration.
* Analysis deletion and ChromaDB cleanup are recoverable.
* Finalization recovers if its task is lost, without duplicating results or changing labels.
* Fairness, privacy, integration, recovery, and end-to-end tests pass.
* Performance targets are measured and reported honestly.
* Controlled deployment, setup, and known limitations are documented.

---

## 17. Out of Scope

Do not add these as implementation tasks unless the PRD is explicitly revised:

* Candidate login or recruiter authentication as an MVP feature
* Public job portal or application submission
* Interview scheduling
* Email or WhatsApp integrations
* Payments
* Mobile app
* General-purpose chatbot
* Fine-tuning or training a custom LLM
* Multi-agent architecture
* Automatic hiring decisions

Authentication and secure deployment controls remain prerequisites before any external exposure with real candidate data, even though full authentication is not an MVP feature.
