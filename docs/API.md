# API.md

# API Contract — AI Resume Analyzer & Job Matching System

> **Status: outline, updated after review.** This document defines endpoint behavior and rules derived from `PRD.md` and `ARCHITECTURE.md`. Items marked **To define** need the team's decision before implementation. Owner: Person 3.

## 1. Purpose

This document is the contract between the API (Person 3) and the application services (Person 2), and between the API and the frontend. It defines what each endpoint does, which analysis states it is allowed in, and what it returns.

If this document conflicts with `ARCHITECTURE.md`, the architecture wins and this document is corrected.

---

## 2. Conventions

* Base path: `/api`
* Format: JSON, except file uploads, which use `multipart/form-data`.
* All IDs are system-generated and encode no personal information.
* Routes stay thin: validate, call an application service, return a response.
* Errors never expose stack traces, file paths, database errors, or secrets.

### Error response shape

Every error uses one shared shape with a stable code:

```json
{
  "error": {
    "code": "ANALYSIS_ALREADY_STARTED",
    "category": "validation",
    "message": "This analysis has already started."
  }
}
```

The frontend responds to the `code`, never to the message text. Categories follow `ARCHITECTURE.md` Section 20: `validation`, `document_extraction`, `duplicate_file`, `requirement`, `matching`, `llm`, `database`, `worker`, and `system`.

Starting set of codes, extended as endpoints are implemented:

* `ANALYSIS_NOT_FOUND`
* `INVALID_ANALYSIS_STATE` (operation not allowed in the current state)
* `ANALYSIS_ALREADY_STARTED`
* `ANALYSIS_PROCESSING` (delete attempted while processing)
* `REQUIREMENTS_INSUFFICIENT`
* `NO_READY_RESUMES`
* `UNSUPPORTED_FILE_TYPE`, `FILE_TOO_LARGE`, `DUPLICATE_FILE`, `RESUME_LIMIT_EXCEEDED`, `UPLOAD_EXPIRED` (per-file reasons)

The full code list is documented here and kept in step with the backend.

### Status codes

* `200` / `201` success
* `202` accepted (deletion started)
* `400` validation error
* `404` analysis or candidate not found, including an analysis marked for deletion
* `409` operation not allowed in the current state (for example uploading after start, starting twice, or deleting while `PROCESSING`)
* `500` unexpected system error

Per-file upload problems (unsupported type, too large, duplicate, limit reached) are reported in the upload response for each file, not as an HTTP error for the whole request.

### Pagination

List endpoints use one convention: `page` (1-based, default 1) and `limit` (default 20, maximum 100). Responses include `total`.

---

---

## 3. Analysis States Used By The API

```text
REQUIREMENTS_PENDING → PROCESSING → RANKED
                          └──────→ FAILED
```

Explanations have their own per-candidate states: `NOT_REQUESTED`, `GENERATING`, `READY`, `FAILED`.

`FAILED` belongs to the entity it describes. For an analysis it means an unrecoverable system-level error, for a resume a document-processing failure, and for an explanation a generation failure. Every response names the entity the status belongs to.

---

## 4. Endpoints

### 4.1 Create analysis

```text
POST /api/analyses
```

Creates an analysis from a job description, either an uploaded file (PDF or DOCX) or pasted text, plus an optional analysis name.

* Extracts job requirements. An uploaded JD file is deleted after requirement extraction, regardless of outcome. Only the extracted requirements and job-relevant text are saved.
* Returns the analysis ID, status `REQUIREMENTS_PENDING`, and the extracted requirements.
* If requirements cannot be reliably identified, returns empty or partial requirements with an indicator that manual input is needed.

### 4.2 List analyses

```text
GET /api/analyses
```

Returns saved analyses with name, candidate count, status, and last-updated time.

Uses the pagination convention in Section 2. Analyses marked for deletion are never listed.

### 4.3 Get analysis

```text
GET /api/analyses/{id}
```

Returns the analysis summary, status, and counts.

### 4.4 Get status

```text
GET /api/analyses/{id}/status
```

Returns progress for polling. The proposed full schema is in Section 6.4. Concept:

```text
{
  "status": "PROCESSING",
  "total": 18,
  "processed": 15,
  "successful": 12,
  "needs_review": 1,
  "failed": 2,
  "duplicates_excluded": 2
}
```

Counts for `total` and `processed` refer to analyzed resumes only. Duplicates and files rejected at upload are reported separately.

Polling: every 2 seconds while the analysis is `PROCESSING` for the first minute, then every 5 seconds, stopping at `RANKED` or `FAILED`. This is a configurable default (`ARCHITECTURE.md` Section 23). Push updates are not part of the MVP.

### 4.5 Delete analysis

```text
DELETE /api/analyses/{id}
```

* Rejected with `409 ANALYSIS_PROCESSING` while the analysis is `PROCESSING`.
* Allowed from `REQUIREMENTS_PENDING`, `RANKED`, and `FAILED`.
* Otherwise the endpoint atomically marks the analysis for deletion and returns `202 Accepted`. The `DELETE` request itself returns only `202`.
* From then on the analysis is hidden: it is excluded from listings, and later read requests (`GET`) return `404 Not Found`.
* Background cleanup deletes vector data and remaining temporary files with retries, then removes the associated database rows (see `ARCHITECTURE.md` Section 11). Failed cleanup remains tracked and retryable.
* A repeated `DELETE` after the marker is set returns `404` and changes nothing, so it cannot bypass cleanup tracking.

### 4.6 Get and edit requirements

```text
GET /api/analyses/{id}/requirements
PUT /api/analyses/{id}/requirements
```

* `PUT` is allowed only in `REQUIREMENTS_PENDING`, otherwise `409`.
* The recruiter can edit, add, and remove required skills, preferred skills, experience requirements, education requirements, and other explicit requirements.

### 4.7 Upload resumes

```text
POST /api/analyses/{id}/resumes
Content-Type: multipart/form-data
```

* Accepts one or more files per request. The frontend may send small batches so that each file shows its own progress.
* Allowed only in `REQUIREMENTS_PENDING`, otherwise `409`.
* Validates file type (PDF or DOCX) and size (10 MB per file).
* Enforces the limit of 50 accepted resumes across the whole analysis, including concurrent requests, at the database level. Duplicates and rejected files do not count. Files beyond the limit are rejected with `RESUME_LIMIT_EXCEEDED`.
* Computes the content hash and detects duplicates within the analysis. A duplicate references the canonical resume, and concurrent uploads of the same content cannot both register.
* Stores accepted files in temporary storage on the shared volume under generated names. No processing starts yet.
* Returns a result for every file in a normal response: status `READY`, `DUPLICATE`, or `REJECTED`, with a reason code where applicable.

Upload outcomes, including rejections, are persisted for later review. The contents of rejected files are never stored.

### 4.7a List resumes

```text
GET /api/analyses/{id}/resumes
```

Returns every uploaded file of the analysis with its filename, status, and reason code. A reopened pending analysis uses this to show the upload step. Files whose temporary copy passed the retention window appear as `REJECTED` with reason `UPLOAD_EXPIRED`, so the recruiter can upload them again.

### 4.8 Start analysis

```text
POST /api/analyses/{id}/start
```

* Allowed only in `REQUIREMENTS_PENDING`, otherwise `409`.
* Validates that the requirements are sufficient and at least one resume is `READY`.
* Saves the confirmed requirements, moves the analysis to `PROCESSING` with a conditional update, and enqueues one task per `READY` resume.
* Returns promptly with the analysis ID and status `PROCESSING` so the frontend can begin polling. It does not wait for extraction, embeddings, or ranking.
* A repeated start finds the analysis no longer `REQUIREMENTS_PENDING` and receives `409` (`ANALYSIS_ALREADY_STARTED`).
* After this call, uploads and requirement edits are rejected.
* If enqueueing fails after the state change, the analysis stays `PROCESSING` and the watchdog re-queues the unfinished resumes.

### 4.9 List candidates

```text
GET /api/analyses/{id}/candidates
```

* Allowed when `RANKED`.
* Returns the ranked candidate list with candidate labels, match score, score breakdown summary, and required-skill coverage. It does not include names or contact details.
* Labels (for example `Candidate 01`) are assigned once when ranking finishes, derived from random candidate IDs, and are stable whenever the analysis is reopened.
* Also returns the separate lists of failed and needs-review files with reasons.
* If no resume produced a result, returns an empty ranking with the failure list.

### 4.10 Get candidate

```text
GET /api/analyses/{id}/candidates/{candidate_id}
```

Returns four separate blocks:

* **Identity:** name and contact details, shown only here.
* **Extracted structured data:** skills, experience, projects, and education.
* **Matching results:** overall score, full score breakdown, matched and missing required and preferred skills, relevant experience evidence, and education match.
* **Explanation:** state and, when `READY`, content.

It never returns raw resume text or the original file. Components that the job did not specify are returned as `not_specified`, not as a pass or fail.

### 4.11 Request explanation

```text
POST /api/analyses/{id}/candidates/{candidate_id}/explanation
```

* Moves the explanation to `GENERATING` with an atomic conditional update (only from `NOT_REQUESTED` or `FAILED`).
* A request from `FAILED` is a retry and is allowed.
* If already `GENERATING` or `READY`, returns the current state and does not start another LLM call. A `READY` explanation cannot be regenerated in the MVP.
* The work runs on the explanation queue.

### 4.12 Get explanation

```text
GET /api/analyses/{id}/candidates/{candidate_id}/explanation
```

Returns the explanation state and, when `READY`, the validated explanation (strengths, gaps, experience alignment, assessment).

---

## 5. State Rules Summary

* Create analysis, edit requirements, upload resumes: only while `REQUIREMENTS_PENDING`.
* Start: only from `REQUIREMENTS_PENDING`.
* List candidates: when `RANKED`.
* Request explanation: when `RANKED`.
* Delete: from `REQUIREMENTS_PENDING`, `RANKED`, or `FAILED`. Rejected while `PROCESSING`. A repeated delete returns `404`.

---

## 6. Response Schemas

> **Proposed — pending DOC-02 shared Pydantic contract freeze.** These schemas are drafted so the frontend can prepare. They are not a finalized contract. Task API-00 finalizes them after the shared types are frozen, and the "Proposed" marking is removed then.

Notation: JSON. Missing values are `null`. Timestamps are ISO 8601 UTC strings. IDs are system-generated strings.

### 6.1 Common types

```text
AnalysisStatus     REQUIREMENTS_PENDING | PROCESSING | RANKED | FAILED
ResumeStatus       READY | DUPLICATE | REJECTED | PROCESSING | SUCCESS | FAILED | NEEDS_REVIEW
ExplanationState   NOT_REQUESTED | GENERATING | READY | FAILED

ScoreComponent     { "status": "scored" | "not_specified" | "indeterminate",
                     "value": number | null }          value is 0 to 100 when scored
EducationMatch     { "status": "met" | "not_met" | "not_specified" | "indeterminate" }
Page               { "page": int, "limit": int, "total": int }
Error              { "error": { "code": string, "category": string, "message": string } }
```

Reason codes are the stable codes in Section 2, plus extraction failure codes defined with the shared extraction-outcome schema in DOC-02.

### 6.2 Analyses and requirements

```text
AnalysisSummary
  id, name, status: AnalysisStatus,
  candidate_count: int,                  ranked candidates only
  failure_reason: string | null,         only when status is FAILED
  created_at, updated_at

AnalysisList       { "items": [AnalysisSummary], ...Page }

CreateAnalysisRequest    multipart: jd_file | jd_text (exactly one), name (optional)
CreateAnalysisResponse   { "analysis": AnalysisSummary,
                           "requirements": Requirements,
                           "needs_manual_input": bool }

Requirements
  required_skills: [string], preferred_skills: [string],
  experience_requirements: [string], education_requirements: [string],
  explicit_requirements: [string], confirmed_at: timestamp | null

UpdateRequirementsRequest   the five lists above (full replacement)
```

### 6.3 Resumes

```text
UploadResumesRequest   multipart: files[]  (one or more)

UploadResult
  "results": [ { "filename": string,
                 "resume_id": string | null,
                 "status": "READY" | "DUPLICATE" | "REJECTED",
                 "reason_code": string | null,
                 "duplicate_of": string | null } ],
  "accepted_count": int,                 accepted resumes now in the analysis
  "limit": 50

ResumeItem             { "resume_id", "filename", "status": ResumeStatus,
                         "reason_code": string | null, "created_at" }
ResumeList             { "items": [ResumeItem] }
```

### 6.4 Start and status

```text
StartResponse    { "analysis_id": string, "status": "PROCESSING" }

StatusResponse
  status: AnalysisStatus,
  total: int,                 accepted resumes (READY when the analysis started)
  processed: int,             resumes in a final status: SUCCESS, FAILED, NEEDS_REVIEW
  successful: int, needs_review: int, failed: int,
  remaining: int,             total minus processed
  duplicates_excluded: int, rejected_excluded: int,   reported separately, not in total
  failure_reason: string | null
```

### 6.5 Candidates

```text
ScoreBreakdown
  semantic_relevance: ScoreComponent,
  required_skill_coverage: ScoreComponent,
  preferred_skill_coverage: ScoreComponent,
  relevant_experience: ScoreComponent,
  education: EducationMatch

CandidateListResponse
  analysis_id, status,
  "ranking": [ { "rank": int, "candidate_id": string, "label": string,
                 "match_score": number,
                 "required_skill_coverage": ScoreComponent,
                 "relevant_experience": ScoreComponent } ],
  "excluded_files": [ { "resume_id", "filename",
                        "status": "FAILED" | "NEEDS_REVIEW",
                        "reason_code": string, "message": string } ]

CandidateDetail
  candidate_id, label, rank,
  identity:  { "name": string, "contact": { "email": string | null,
                                              "phone": string | null,
                                              "other": [string] } },
  extracted: { "skills": [string], "experience": [object],
               "projects": [object], "education": [object] },   shapes from DOC-02
  matching:  { "match_score": number,
               "breakdown": ScoreBreakdown,
               "required_skills":  { "matched": [string], "missing": [string] },
               "preferred_skills": { "matched": [string], "missing": [string] },
               "experience_evidence": [ { "summary": string } ] },
  explanation: { "state": ExplanationState }
```

The ranking list never contains the `identity` block. Raw resume text is never returned.

### 6.6 Explanations

```text
ExplanationResponse
  state: ExplanationState,
  explanation: { "strengths": [string], "gaps": [string],
                 "experience_alignment": string, "assessment": string,
                 "generated_at": timestamp } | null,       only when READY
  failure_reason: string | null                            only when FAILED
```

The request endpoint takes no body.

---

## 7. Open Decisions

* Complete list of error codes, which grows as endpoints are implemented
* Extraction failure reason codes, defined with the shared extraction-outcome schema (DOC-02)
* Exact shapes of the extracted experience, project, and education objects (DOC-02)
