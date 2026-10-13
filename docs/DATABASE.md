# DATABASE.md

# Data Model — AI Resume Analyzer & Job Matching System

> **Status: conceptual outline, updated after review.** This document lists the entities, key fields, statuses, and constraints required by `PRD.md` and `ARCHITECTURE.md`. It is not the final schema. Items marked **To define** need the team's decision before implementation. Owner: Person 2.

## 1. Purpose

PostgreSQL is the source of truth for structured application data. This document defines what is stored, what is not, and the constraints that enforce the architecture.

If this document conflicts with `ARCHITECTURE.md`, the architecture wins and this document is corrected.

---

## 2. What Is Not Stored

* **Raw resume files.** They are deleted after the extraction attempt.
* **Raw job description files.** They are deleted after requirement extraction.
* **Raw resume text.**
* **Vector embeddings.** They live in ChromaDB, one collection per analysis.
* **Anything not required for recruiter review.**

---

## 3. Entities

### 3.1 Analysis

* Analysis ID (system-generated)
* Name
* Status: `REQUIREMENTS_PENDING`, `PROCESSING`, `RANKED`, or `FAILED`
* Failure reason (only when `FAILED`, which means an unrecoverable analysis-level error, for example `FINALIZATION_FAILED`)
* Deletion requested timestamp (empty unless deletion is in progress; this is a marker, not a lifecycle state)
* Scoring configuration version used
* Created and updated timestamps

### 3.2 JobRequirements

One per analysis.

* Analysis ID
* Required skills (canonical)
* Preferred skills (canonical)
* Experience requirements
* Education requirements
* Other explicit requirements
* Job-relevant text derived from the job description (used for semantic matching)
* Confirmed timestamp

### 3.3 Resume

One per uploaded file, including duplicates and rejected files. The contents of rejected files are never stored; only the outcome is kept so the recruiter can review it later.

* Resume ID
* Analysis ID
* Original filename (needed to report failed, duplicate, and needs-review files)
* Content hash
* Status: `READY`, `DUPLICATE`, `REJECTED`, `PROCESSING`, `SUCCESS`, `FAILED`, or `NEEDS_REVIEW` (transitions in Section 5)
* Failure category and reason code (for failed, rejected, and needs-review)
* Canonical resume reference (for duplicates)
* Temporary storage key (a generated name, never the original filename; cleared when the raw file is deleted)
* Processing started timestamp (set when a worker claims the resume)
* Retry count
* Timestamps

### 3.4 Candidate

One per successfully processed resume.

* Candidate ID (system-generated, encodes no personal information)
* Analysis ID and Resume ID
* Display label, for example `Candidate 01`: empty until ranking finishes, then assigned once and never recomputed (sequential, zero-padded, assigned inside the finalization transaction)
* Display data: name and contact details (shown only on the candidate detail screen)
* Extracted structured data: skills, experience, projects, education (canonical)

### 3.5 MatchResult

One per candidate.

* Candidate ID
* Component scores: semantic relevance, required-skill coverage, preferred-skill coverage, relevant experience, education / explicit requirements (each may be `not_specified`)
* Final score and rank
* Matching evidence (matched and missing skills, experience evidence)
* Scoring configuration version

### 3.6 Explanation

One per candidate.

* Candidate ID
* State: `NOT_REQUESTED`, `GENERATING`, `READY`, or `FAILED`
* Validated explanation content (when `READY`)
* Generation started timestamp (used for the timeout)
* Failure reason (when `FAILED`; a new request may retry from this state)
* Timestamps

---

## 4. Storage Approach

Use relational columns for identity, state, and relationships, and JSONB for structured payloads that are likely to evolve.

* **Relational columns:** analysis state and timestamps, resume status and canonical reference, candidate label and identity fields, match score and rank, explanation state.
* **JSONB:** job requirement lists, extracted experience, projects, and education, score breakdown and matching evidence, and validated explanation content.
* Candidate name and contact details are separate, explicit fields, never inside the extracted-data payload.
* Every JSONB payload has an explicit Pydantic schema. JSONB is not a place to store an unvalidated candidate object.
* Individual payloads can be normalized into tables later if query patterns or integrity needs justify it.

---

## 5. Statuses and Constraints

### Resume status transitions

A resume is created with one of three initial statuses:

```text
READY
DUPLICATE
REJECTED
```

Only `READY` moves on:

```text
READY → PROCESSING → SUCCESS
                   → FAILED
                   → NEEDS_REVIEW
```

`DUPLICATE` and `REJECTED` are final for processing. They are never queued and never create a candidate.

A worker claims a resume with a conditional update from `READY` to `PROCESSING` and records the start time. If the claim fails, another worker already owns the resume. A stale `PROCESSING` resume past the claim window returns to `READY` for a limited number of retries, then becomes `FAILED`.

The one transition into `REJECTED` after creation is expiry: a `READY` resume in a `REQUIREMENTS_PENDING` analysis whose temporary file passes the retention window becomes `REJECTED` with reason `UPLOAD_EXPIRED`. Rejected resumes do not count toward the 50-resume limit.

### Status ownership

`FAILED` belongs to the entity it describes. Analysis `FAILED` means an unrecoverable system-level error. Resume `FAILED` means a document-processing failure. Explanation `FAILED` means a generation failure. Each entity has its own status set, and an unrelated value is never reused across entities.

### Integrity constraints

* **Foreign keys** link every entity to its parent: requirements, resumes, candidates, match results, and explanations belong to an analysis or candidate.
* **One per parent:** one `JobRequirements` per analysis, one `MatchResult` per candidate, one `Explanation` per candidate.
* **Duplicate invariant.** Within one analysis, only one canonical resume record may own a given content hash. Duplicate records reference that canonical record and cannot create candidate records or processing tasks. This is enforced by a partial unique index on analysis ID and content hash that excludes duplicate rows. The insert is the check, not a prior lookup, so concurrent uploads of the same content are safe.
* **Accepted-resume limit.** At most 50 accepted resumes per analysis, excluding duplicate and rejected resumes. Enforced at the database level so concurrent upload requests cannot exceed it, for example by locking the analysis row while accepted resumes are counted and registered in one transaction. Default mechanism: lock the analysis row in the same transaction. Any other mechanism needs team agreement and documentation.
* **Unique rank** within an analysis among ranked candidates.
* **Unique label** within an analysis once assigned. The label is empty until ranking finishes, so uniqueness applies only to assigned labels.
* **Valid status values** for each entity, through enum or check constraints, with required fields not null.
* **Atomic state changes.** Analysis status and explanation state change only through conditional updates:
  * `REQUIREMENTS_PENDING` to `PROCESSING` only once.
  * `PROCESSING` to `RANKED` only once, inside the finalization transaction, so finalization is safe to run twice or concurrently.
  * Explanation to `GENERATING` only from `NOT_REQUESTED` or `FAILED`.
* **Finalization transaction.** Finalization locks the analysis row, exits if the status is not `PROCESSING`, writes ranks and labels, sets `RANKED`, and commits as one transaction. The unique rank and label constraints are a backstop. A partially finalized analysis is never visible.
* **No ranking for failed files.** Only candidates with a `MatchResult` appear in rankings. Failed, rejected, and needs-review resumes have no candidate record and no score.
* **System-generated IDs.** Candidate IDs and the final tie-breaker are unrelated to personal attributes. Labels are derived from candidate IDs, never from rank, upload order, or filename.

### Starting indexes

* Analyses by last-updated time, excluding those marked for deletion
* Resumes by analysis and status
* Candidates by analysis
* Match results by analysis and rank
* Explanations by state

---

## 6. Deletion

PostgreSQL and ChromaDB cannot share one atomic transaction, so deleting an analysis is a tracked, retryable operation and not just a database cascade:

1. Allow the request from `REQUIREMENTS_PENDING`, `RANKED`, and `FAILED`, and reject it while the analysis is `PROCESSING`. A repeated request after the marker is set returns not found and changes nothing.
2. Set the deletion requested marker. The analysis is hidden from all listings and reads immediately.
3. Delete the ChromaDB collection and embeddings and any remaining temporary files, retrying on failure.
4. Delete the analysis rows (requirements, resumes, candidates, match results, explanations) only after the vector data is gone.

If vector deletion fails, the marker stays and the cleanup job retries. An analysis is never treated as fully deleted while vector data remains.

A periodic sweep also removes ChromaDB collections that no longer correspond to any analysis.

---

## 7. Recovery Support

The schema must let the watchdog find unfinished work:

* `READY` resumes of a `PROCESSING` analysis that no worker has claimed within the claim window, which covers enqueue failure.
* `PROCESSING` resumes whose start time is older than the claim window (stale), handled by the retry rule in Section 5.
* Explanations stuck in `GENERATING` past the timeout. A stale `GENERATING` state is set to `FAILED`, and a later explicit request may retry it.
* Analyses still `PROCESSING` after every associated resume reached a final status (lost finalization), for which finalization is enqueued again. Finalization is idempotent and never duplicates match results or changes labels. An analysis already marked `FAILED` is never re-enqueued.
* `READY` resumes in `REQUIREMENTS_PENDING` analyses whose temporary file passed the retention window.
* Analyses stuck in `PROCESSING`.
* Analyses with a deletion marker whose cleanup is unfinished.
* Temporary files with no matching active resume record.

Status and timestamps are the source of truth for recovery. The task queue is not.

---

## 8. Open Decisions

* Detailed cascade order inside the deletion process

Initial values for the migration tool, timeouts, retention, and retry limits are set in `ARCHITECTURE.md` Section 23. They are configurable.
