# RULES.md

# Project Rules — AI Resume Analyzer & Job Matching System

## 1. Purpose

These rules define how the project is developed, tested, reviewed, and maintained.

They apply to human developers, AI coding assistants, code-generation tools, and automated development workflows.

This document contains **rules, not facts**. Facts such as endpoints, states, ownership, limits, and schemas live in their source documents and are referenced here, never copied. Copied facts drift out of date.

---

## 2. Source of Truth

When making implementation decisions, use this priority order:

1. `PRD.md` — what the product must do
2. `ARCHITECTURE.md` — how the system is structured
3. `API.md` and `DATABASE.md` — backend contracts and data model
4. `DESIGN.md` — how the product looks and behaves
5. `RULES.md` — development and implementation constraints
6. `TASKS.md` — current implementation work
7. Existing code — the current implementation, but not authority over the documents above

If code conflicts with a documented decision, do not silently change the architecture or requirements. Raise the conflict before making a broad change.

If two documents conflict, the higher-priority document wins, and the lower-priority one is corrected.

---

## 3. Working Rules

### 3.1 Small Changes

Implement work in small, independently testable tasks. Do not combine unrelated changes.

A task should have a clear objective, defined files or modules, acceptance criteria, tests, and a reviewable scope. Avoid large "implement everything" changes.

### 3.2 Implementation Loop

For every meaningful task:

```text
Read → Understand → Plan → Implement → Test → Review → Fix → Commit
→ Update documentation if needed
```

Before modifying an existing module, read it, understand its responsibility, check related interfaces and ownership, and identify affected tests. Do not modify unfamiliar code based only on filenames or assumptions.

### 3.3 No Unnecessary Rewrites

Do not rewrite working modules to make them look cleaner. Refactoring needs a clear reason: correctness, maintainability, security, performance, architectural consistency, or testability. Avoid unrelated refactoring during feature work.

---

## 4. Architecture Rules

### 4.1 Layer Boundaries

Follow the layers in `ARCHITECTURE.md` Section 2. A layer must not bypass another layer without an explicit architectural reason.

### 4.2 API Routes Stay Thin

Routes validate requests, call application services, return responses, and map errors. At upload time the API layer may also validate file type and size and compute the content hash, as the architecture specifies.

Routes must not contain extraction logic, matching algorithms, score calculation, embedding generation, ChromaDB lifecycle logic, LLM prompting, or long-running processing.

### 4.3 Long-Running Work

CPU-heavy or long-running operations never run inside FastAPI request handlers. They run as background tasks through Celery, Redis, and workers. This covers resume extraction, embedding generation, matching, batch processing, and AI explanation generation.

### 4.4 Replaceable Components Use Interfaces

Access these only through interfaces: document loading, embeddings, the vector store, the LLM, and task execution. Business logic must not import vendor-specific code directly.

### 4.5 No Silent Architecture Changes

Do not change a documented architectural decision without team approval and a documentation update (see Section 25).

---

## 5. Ownership Rules

Ownership is defined in `ARCHITECTURE.md` Section 3. These rules govern how it is applied.

* Skill normalization belongs to Person 1 only. No one else implements competing synonym logic.
* Person 2 consumes canonical structured output and must not duplicate extraction or normalization.
* Scoring, ranking, orchestration, persistence, and the Profile Builder belong to Person 2.
* All LLM work belongs to Person 3 and is limited to AI-generated explanations.
* The PII-detection utility is built by Person 1 and integrated into the Profile Builder by Person 2.
* The evaluation dataset is a shared early team task.

### Cross-boundary changes

Owning a module means primary responsibility, not exclusive access. Any change inside another person's area needs that owner's review before merging.

---

## 6. Shared Contract Rules

Person 1 and Person 2 communicate only through the shared Pydantic schemas. The schemas must be explicit, typed, version-controlled, validated, and documented. Do not change them silently.

For a breaking change:

1. Discuss it with both owners.
2. Update the shared schema.
3. Update both producer and consumer.
4. Update tests.
5. Update documentation.

---

## 7. Scoring and Fairness Rules

### 7.1 Only ScoringProfile Enters Matching

The matching engine receives only the approved `ScoringProfile` (see `ARCHITECTURE.md` Section 8). It never receives the full candidate object or the raw resume.

### 7.2 No Raw Resume Concatenation

`job_relevant_text` is built only from approved sections: experience responsibilities, project descriptions, technical skills, and other explicit professional content. Never concatenate the whole resume.

### 7.3 Deterministic Scrubbing

Free-text scrubbing must be deterministic and must:

1. Remove every occurrence of the extracted name, email, phone number, and institution names for that resume.
2. Remove other personal identifiers found by the shared PII-detection utility.
3. Replace gendered pronouns and gendered terms with a neutral placeholder.

Institution names never influence semantic similarity. A job that explicitly requires a specific institution or credential is handled as a structured requirement.

### 7.4 Personal Attributes

Matching must not depend on name, contact information, photo, age, gender indicators, marital status, religion, caste, or other irrelevant personal attributes.

### 7.5 Fairness Tests

Fairness is tested, not assumed. Tests use pairs of profiles with identical job-relevant content and different personal information, covering both structured fields and free text.

A pair passes only if the scrubbed `job_relevant_text` is identical, all structured components are exactly equal, and score, evidence, and ranking are identical. A pair that fails reveals a scrubbing defect to be fixed.

### 7.6 Determinism

Scoring and ranking must be deterministic. The same inputs and configuration must produce the same result.

* Pin model versions and dependency versions.
* Keep weights and thresholds in versioned configuration. Do not hard-code unexplained weights across the codebase.
* Record the configuration version with each result.

### 7.7 Independence from the LLM

The matching engine is explainable, testable, and independent of the LLM.

---

## 8. Ranking Rules

Rank by the matching score and apply the tie-breakers in `ARCHITECTURE.md` Section 9, in that order. The final tie-breaker is a system-generated candidate ID that encodes no personal attributes.

Ranking must be deterministic.

---

## 9. LLM Rules

### 9.1 What the LLM May and Must Not Do

The LLM may explain matching results, summarize strengths and gaps, and explain experience alignment.

The LLM must not calculate or modify scores, re-rank candidates, decide whether to hire, introduce new matching criteria, or override deterministic results.

### 9.2 Grounded Generation

Explanations are generated only from approved structured data and matching evidence. The model must not invent skills, experience, education, projects, qualifications, responsibilities, or achievements. If information is unavailable, the explanation must say so.

Do not send unnecessary identifying information to the LLM.

### 9.3 Output Validation

LLM output must pass the output parser, schema validation, and grounding validation before it is stored or displayed. Invalid output never enters the database silently.

### 9.4 Explanation Lifecycle

Explanation state belongs to each candidate (see `ARCHITECTURE.md` Section 15).

* Moving to `GENERATING` is an atomic conditional database update, allowed only from `NOT_REQUESTED` or `FAILED`.
* A candidate that is `GENERATING` or `READY` never triggers another LLM call.
* A timeout moves a stuck `GENERATING` state to `FAILED`.
* A failed explanation can be retried by a new request. A successful explanation is never regenerated in the MVP.
* Explanation generation runs on its own queue, separate from resume processing.
* A failed explanation never affects the score or ranking.

---

## 10. Analysis Lifecycle Rules

The states and transitions are defined in `ARCHITECTURE.md` Section 11.

* Analysis state ends at `RANKED` or `FAILED`. There is no analysis-level `EXPLAINING` or `COMPLETE` state.
* Resume processing never begins before the recruiter confirms sufficient job requirements and explicitly starts the analysis.
* If requirements cannot be reliably identified, the recruiter must be able to provide them manually.
* After start, uploads and requirement edits are locked.
* If every resume fails, the analysis still ends in `RANKED` with an empty ranking and a failure list. `FAILED` is reserved for unrecoverable system-level errors.
* Start returns promptly and does not wait for processing. A repeated start receives a conflict response.
* Deletion is allowed from `REQUIREMENTS_PENDING`, `RANKED`, and `FAILED`, and rejected while the analysis is `PROCESSING`. A repeated delete after the marker is set returns not found and changes nothing.
* Deletion is a tracked, retryable operation: mark the analysis, hide it immediately, delete vector data and temporary files, then delete database rows. Never report deletion as complete while vector data remains.
* Status changes use conditional updates so that concurrent or repeated operations have no extra effect.
* Finalization runs as one transaction: lock the analysis row, exit if the status is not `PROCESSING`, write ranks and labels, set `RANKED`, commit. It must be safe to run twice and concurrently, and an analysis is never `RANKED` with a partial result.

---

## 11. Resume Processing Rules

* Each resume is processed independently. One failed resume never stops the others.
* Failed and needs-review resumes are never scored or ranked and never appear as low-scoring candidates.
* Resumes are created as `READY`, `DUPLICATE`, or `REJECTED`. Only `READY` resumes are processed (`PROCESSING`, then `SUCCESS`, `FAILED`, or `NEEDS_REVIEW`). `DUPLICATE` and `REJECTED` are never queued.
* Duplicates are detected at upload by content hash, never by filename. A database constraint allows one canonical resume per hash within an analysis, and duplicates reference it. Duplicates are reported to the recruiter and never create candidate records.
* The 50-resume limit counts accepted resumes only (not duplicates or rejected files) and is enforced at the database level so concurrent uploads cannot exceed it.
* Candidate labels are assigned once after ranking, derived from random candidate IDs, stored, and never recomputed. They never depend on rank, upload order, or filename. Assignment happens in the finalization transaction, only for candidates that have no label yet.
* A status belongs to one entity. `FAILED` means a different thing for an analysis, a resume, and an explanation, and the code must always make clear which one.
* Resume tasks must be idempotent and retryable, keyed by `analysis_id` and `resume_id`.
* A worker claims a resume with a conditional update from `READY` to `PROCESSING` before doing any work, and exits if the claim fails. Stale `PROCESSING` resumes are retried a limited number of times by the watchdog, then marked `FAILED`.
* Processing must handle worker restarts, failed tasks, retries, interrupted processing, and orphaned temporary files.
* A watchdog must detect and recover or fail analyses stuck in `PROCESSING`. It must also re-enqueue finalization when an analysis stays `PROCESSING` after every resume reached a final status, and finalization must never change existing labels or duplicate results.
* Transient finalization errors are retried with backoff, up to 2 automatic retries after the initial attempt (3 attempts in total, configurable). Other errors or exhausted retries mark the analysis `FAILED` with reason `FINALIZATION_FAILED`. Delivery failures are recovered by the watchdog and do not count as failed attempts. The watchdog never re-enqueues finalization for a `FAILED` analysis.

---

## 12. Privacy Rules

* Raw files are never retained longer than needed. A file rejected at upload is not kept, a duplicate's file is deleted immediately at upload, and an accepted file is deleted when its extraction attempt ends, regardless of outcome. An uploaded job description file follows the same rule: it is deleted when requirement extraction ends.
* Downstream processing and explanations use structured extracted data, never raw files.
* Raw resume text is never displayed in the application.
* Orphaned temporary files are removed by the cleanup job.
* In a pending analysis, files that pass the retention window are deleted and shown as expired (`REJECTED` with reason `UPLOAD_EXPIRED`).
* Deleting an analysis deletes its database records, explanations, ChromaDB collection and embeddings, and remaining temporary files, through the tracked process in `ARCHITECTURE.md` Section 11.
* Saved results contain only information required for recruiter review.
* The MVP runs in a controlled environment. It must not be deployed publicly with real candidate data, and it is not exposed without authentication.
* Candidate data stays within the controlled environment, including AI processing.

---

## 13. File Upload Security

Uploaded files are untrusted input.

* Validate file type, size, and content. Never trust the filename or MIME type alone.
* Enforce the limits in `PRD.md` Section 15.
* Never execute uploaded files.
* Never store uploaded resumes in Git.
* Temporary files live on the shared volume under generated names. Never use the original filename as a storage path.

---

## 14. Data Store Rules

* PostgreSQL is the source of truth for persistent application state.
* ChromaDB holds only vectors, isolated by analysis, with one collection per analysis. A periodic sweep removes orphaned collections that no longer match any analysis.
* Database access goes through the persistence and application layers. No SQL inside React components, and no database credentials exposed to the frontend.
* Schema changes follow `DATABASE.md` and are applied through versioned migrations.
* Use relational columns for identity and state and JSONB for evolving payloads. Every JSONB payload has an explicit Pydantic schema and is never an unvalidated object.

---

## 15. API and Frontend Rules

* The API follows `ARCHITECTURE.md` Section 5 and `API.md`. Do not invent endpoint behavior independently in the frontend and backend.
* The frontend contains no matching or scoring logic.
* The frontend follows `DESIGN.md`, including its constraints in Section 26. Use shared components. Do not introduce unapproved colors, spacing, card styles, chatbot-style layouts, or unnecessary animations.
* Candidate names and contact details appear only on the candidate detail screen.
* Requirements the job did not specify are shown as "not specified", never as a pass or fail.
* Every important state is represented: loading, empty, success, error, processing, failed, needs review, duplicate.

---

## 16. Error Handling

Errors must be specific, understandable, actionable, and safe for users.

Never expose stack traces, database errors, internal file paths, secrets, or infrastructure details.

Bad: `Something went wrong.`

Better: `The resume could not be processed because no reliably extractable text was found.`

---

## 17. Testing Rules

Every meaningful feature has appropriate tests across the levels in `ARCHITECTURE.md` Section 18.

At minimum, test:

* Requirement extraction and skill normalization
* Resume extraction
* Profile Builder and scrubbing
* Scoring, ranking, and tie-breaking
* Duplicate detection
* Failure and needs-review handling
* State transitions, finalization, and the delete rule
* Raw-file deletion and ChromaDB cleanup
* LLM output validation and explanation state transitions
* Fairness behavior

### Test data

Tests, fixtures, and evaluation data use synthetic or properly anonymized or consented data only. Never use real candidate resumes in tests or commit them to the repository.

---

## 18. No Silent Fallbacks

Do not silently replace a failed component with an unrelated implementation.

* Failed extraction: do not use raw text for scoring.
* Failed embedding: do not silently change scoring behavior.
* Failed LLM response: do not invent an explanation.
* Missing requirement: do not assume one.
* Missing candidate information: do not infer it.

Failures must be explicit and observable.

---

## 19. Logging Rules

Logs help diagnose failures without exposing candidate data.

Never log raw resumes, resume text, contact information, unnecessary candidate PII, secrets, API keys, or passwords.

Prefer identifiers and metadata: `analysis_id`, `resume_id`, `candidate_id`, `task_id`, status, error category, and processing duration.

---

## 20. Secrets and Configuration

Never commit API keys, passwords, database credentials, tokens, or `.env` files containing secrets.

Use environment variables and provide a `.env.example` with placeholder values only.

---

## 21. Dependency Rules

Before adding a dependency:

1. Check whether the existing stack already solves the problem.
2. Confirm that it is necessary.
3. Prefer established, maintained libraries.
4. Avoid duplicate libraries for the same purpose.
5. Pin its version and document important architectural dependencies.

LangChain is used selectively, for infrastructure such as document loading, embedding, vector-store, and LLM integration. Do not use it where plain Python is clearer. Core logic stays ordinary application code.

---

## 22. Git and Review Rules

### Commits

Commits are coherent and descriptive.

```text
feat: add requirement extraction
fix: handle corrupted resume extraction
test: add ranking tie-breaker tests
refactor: simplify profile builder
docs: update API contract
```

Avoid commits such as `changes`, `update`, `final`, or `stuff`.

### Pull requests

* Work happens on branches. No direct commits to the main branch.
* Every change merges through a pull request with at least one reviewer who is not the author.
* A change inside another person's ownership area needs that owner's approval.
* A change to the shared Pydantic schemas needs approval from both Person 1 and Person 2.
* A change to a project document follows Section 25.

### Never commit

Secrets, candidate resumes, temporary files, generated private data, local databases, and unnecessary build artifacts.

---

## 23. AI Coding Assistant Rules

AI coding tools must:

1. Read the relevant project documents before implementing.
2. Inspect existing code before modifying it.
3. Respect ownership boundaries and the documented architecture.
4. Avoid changing unrelated files.
5. Explain significant architectural changes.
6. Generate tests with meaningful feature changes.
7. Never invent APIs or database structures without checking `API.md` and `DATABASE.md`.
8. Never introduce an LLM into a non-LLM component without explicit approval.
9. Never weaken privacy or security requirements to make implementation easier.
10. Never be given real candidate data. Real resumes and personal data must not be pasted into external AI tools.

If an AI tool believes a documented decision could be improved, it may suggest the change. It must not implement the alternative unless the team explicitly approves it.

---

## 24. Definition of Done

A task is complete when:

* Implementation is finished and relevant tests pass.
* Error handling exists.
* Security, privacy, and fairness requirements are respected.
* Architecture and ownership boundaries are respected.
* The UI follows `DESIGN.md`.
* Documentation is updated where necessary.
* No unrelated changes were introduced.
* The diff has been reviewed.

Code that merely runs is not complete.

---

## 25. Change Management

Changes to project documents must be intentional.

If a change affects product scope, architecture, ownership, data flow, privacy, scoring, fairness, or API and database contracts, update the relevant document first, then implement dependent code. Implementation must not silently redefine the specification.

---

## 26. Non-Negotiable Rules

These must not be violated without an explicit architecture or product decision:

1. The LLM does not calculate or modify candidate scores.
2. Only `ScoringProfile` enters the matching engine.
3. Personal information must not influence matching, and fairness is tested.
4. Skill normalization belongs to Person 1.
5. Scoring, ranking, orchestration, and persistence belong to Person 2.
6. LLM integration and AI explanations belong to Person 3.
7. Requirements must be confirmed and the analysis explicitly started before resume processing.
8. Long-running processing uses background workers.
9. One failed resume does not stop valid resumes.
10. Failed and needs-review resumes are never scored or ranked.
11. Duplicates are detected at upload by content hash with a database constraint, and the 50-resume limit counts accepted resumes and is enforced at the database level.
12. Ranking is available before AI explanations.
13. Explanation state is per candidate, changes atomically, never triggers duplicate LLM calls, and allows retry only after failure.
14. Raw resumes and uploaded job description files are deleted after their extraction attempt, and raw resume text is never displayed.
15. Analysis deletion is tracked and retryable, removes all associated data including vectors, and is blocked while `PROCESSING`.
16. Scores and rankings are deterministic and testable.
17. No secrets or candidate resumes are committed to Git, and no real candidate data goes into AI tools.
18. No unauthorised architectural changes, including by AI coding tools.
19. Final hiring decisions remain with the human recruiter.
20. Candidate labels are assigned once after ranking and never recomputed.
21. Finalization is one transaction, safe under concurrent runs, recoverable by the watchdog, and a failure marks the analysis `FAILED` without a partial result.
