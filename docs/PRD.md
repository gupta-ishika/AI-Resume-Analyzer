# PRD — AI Resume Analyzer & Job Matching System

## 1. Product

**AI Resume Analyzer & Job Matching System**

---

## 2. Problem

Recruiters receive many resumes for a job, making manual comparison is time-consuming and inconsistent.

Keyword-only matching can fail when:

* Equivalent skills use different names.
* Experience is described differently.
* Resumes contain irrelevant keywords.
* Required skills are missing.
* Candidates have different levels of relevant experience.

The system helps recruiters screen, compare, and understand candidates efficiently.

---

## 3. Target User

**Recruiter / HR professional**

The recruiter needs to:

* Provide a job description.
* Upload multiple resumes.
* Identify relevant candidates.
* Understand why candidates are ranked differently.
* Review skill gaps and compare relevant experience.

---

## 4. Product Goal

Help recruiters:

1. Analyze a job description.
2. Analyze multiple resumes.
3. Identify relevant qualifications.
4. Rank candidates using explainable matching criteria.
5. Understand candidate strengths and gaps through AI-generated explanations.

The system is a **decision-support tool**, not an automated hiring decision-maker.

---

## 5. Core User Flow

```text
Recruiter
    ↓
Provide Job Description
    ↓
Review / Provide Job Requirements
    ↓
Upload Multiple Resumes
    ↓
Analyze Documents
    ↓
Extract Relevant Information
    ↓
Compare Candidates
    ↓
Calculate Match Scores
    ↓
Rank Candidates
    ↓
Generate AI Explanations
    ↓
Recruiter Reviews Results
```

---

## 6. MVP Scope

### 6.1 Job Description

The recruiter can upload or paste a job description.

The system should identify:

* Required skills
* Preferred / nice-to-have skills
* Experience requirements
* Education requirements
* Other explicitly stated job requirements

The recruiter must be able to review and edit the extracted requirements. If requirements cannot be reliably identified, see Section 14.5.

### 6.2 Resumes

The system must support multiple resumes per analysis.

For each valid resume, identify:

* Candidate name
* Skills
* Work experience
* Relevant responsibilities
* Projects
* Education

Certification extraction is not required for the MVP.

---

## 7. Candidate Matching

Candidate matching must consider multiple job-relevant factors.

### 7.1 Semantic Relevance

Measure how relevant the candidate's job-relevant information is to the job description. Semantic matching should use job-relevant candidate information rather than the entire raw resume, where possible.

### 7.2 Required Skill Coverage

Determine how many required skills are supported by the candidate.

Skill matching must normalize equivalent names, for example:

```text
JS → JavaScript
Postgres → PostgreSQL
React.js → React
```

Missing required skills must be clearly identified.

### 7.3 Preferred Skill Coverage

Preferred skills must be considered separately from required skills. A missing preferred skill must not be treated the same way as a missing required skill.

### 7.4 Relevant Experience

Evaluate experience relevant to:

* Required skills
* Job responsibilities
* Role requirements
* Relevant technologies/domains

Irrelevant work experience should not contribute the same value as directly relevant experience.

### 7.5 Education and Explicit Requirements

Education and other explicit requirements affect matching only when they are stated in the JD.

---

## 8. Candidate Score

The candidate score must combine:

* Semantic relevance
* Required skill coverage
* Preferred skill coverage
* Relevant experience
* Education / explicit requirements

The exact weighting is not fixed in the PRD. Weights must be:

1. Defined during implementation.
2. Tested against the evaluation dataset.
3. Documented as a design decision.

The system must display a score breakdown, not just one unexplained number.

---

## 9. Candidate Ranking

Candidates are ranked by their calculated matching score. Ranking must be deterministic for equal or near-equal scores.

Tie-breaking order:

1. Higher required-skill coverage
2. Higher relevant-experience score
3. Higher semantic relevance
4. System-generated candidate identifier (unrelated to personal attributes)

---

## 10. Explainability

For every candidate, the system should show:

* Overall match score
* Semantic relevance
* Required skill coverage
* Preferred skill coverage
* Relevant experience
* Education / explicit requirement matching
* Matched required skills
* Missing required skills
* Matched preferred skills
* Missing preferred skills
* Relevant experience explanation

The recruiter should be able to understand why a candidate received their ranking.

---

## 11. Role of AI Explanation

The LLM explains matching results; it does not calculate them. The numerical score must come from the matching engine.

The LLM may generate:

* Candidate summary
* Strengths
* Relevant qualifications
* Skill gaps
* Experience alignment
* Explanation of the overall assessment

The explanation must be based only on information extracted from the candidate and the calculated matching results.

The LLM must not invent:

* Skills
* Experience
* Education
* Projects
* Qualifications
* Achievements

---

## 12. Fairness

The candidate score must not be influenced by irrelevant or sensitive personal attributes, including:

* Gender
* Photo
* Age
* Name
* Marital status
* Religion
* Caste
* Other sensitive or irrelevant personal information

Matching must focus on job-relevant qualifications. Personally identifying information should be separated from scoring where reasonably possible.

The final hiring decision remains with the human recruiter.

---

## 13. Privacy

For the MVP:

* Candidate data must remain within the controlled application environment, including AI explanation processing.
* Candidate resumes must not be publicly exposed.
* Raw resumes must not be committed to Git.
* Candidate data must not unnecessarily appear in logs.
* Secrets must not be stored in source code.
* Saved analysis results should contain only information required for recruiter review.
* Recruiters must be able to delete saved analysis results.

### Raw Resume Retention

Raw uploaded resumes must be deleted after the extraction attempt for each file completes, regardless of outcome. This includes successful, corrupted, unsupported, scanned or image-only, failed, and duplicate files.

Downstream matching and AI explanations must use the structured extracted data and matching evidence, not the raw resume. Temporary files left by interrupted processing must be removed by the application's cleanup mechanism.

### Job Description Files

An uploaded job description file must be deleted after requirement extraction completes, regardless of outcome. Only the extracted requirements and the job-relevant text derived from the job description are saved with the analysis.

---

## 14. Failure Handling

### 14.1 Scanned / Image-Only PDF

If a PDF has no reliably extractable text and would require OCR (not supported in the MVP), the system must mark the resume as failed and must not assign it a low score. The recruiter should be asked to upload a text-based PDF or DOCX.

### 14.2 Corrupted File

The system must detect the failure, show a clear error, and exclude the file from matching.

### 14.3 Unsupported Format

The system must clearly inform the recruiter that the file format is unsupported.

### 14.4 Unusual Layout

If extraction succeeds but the document structure is unreliable, flag the resume for review and avoid silently producing a misleading low score.

### 14.5 Invalid Job Description

If required matching criteria cannot be reliably determined:

* Inform the recruiter.
* Allow manual review and editing of requirements.
* Do not proceed with normal ranking until sufficient criteria are available.

### 14.6 Partial Failures

A failure in one resume must not stop the entire analysis.

```text
20 resumes uploaded
17 successfully analyzed
3 failed
        ↓
Rank the 17 valid candidates
        ↓
Show 3 failed resumes separately
```

The recruiter must be able to see which files failed and why.

### 14.7 Duplicate Resumes

Duplicates are detected using a content hash. If the same file content appears multiple times in one analysis, process it once, avoid duplicate candidate entries, and clearly indicate that a duplicate was detected.

---

## 15. Input Constraints

* Supported formats: PDF and DOCX (digitally generated)
* Maximum 10 MB per resume
* Maximum 50 accepted resumes per analysis (duplicates and rejected files do not count)
* English language only (resumes and job descriptions)

---

## 16. Performance

These are target benchmarks, not unconditional guarantees, measured on the defined reference environment:

* Up to 20 resumes: ranked results within 60 seconds
* Up to 50 resumes: ranked results within 150 seconds
* Individual AI explanation: within 15 seconds

Ranked results must be displayed before waiting for all AI explanations. Actual performance will be benchmarked during implementation.

---

## 17. Quality Requirements

The system will be evaluated using a representative evaluation dataset.

### Skill Extraction

* Precision ≥ 90%
* Recall ≥ 85%

### Ranking

For a set of 20 candidates, a human-labelled top-5 shortlist is compared with the system's top-5. Overlap should be at least 80%.

These values are evaluation targets and must be validated experimentally.

---

## 18. Fairness Evaluation

The system must include tests where only irrelevant personal attributes are changed and job-relevant information stays identical.

```text
Job-relevant information = same
Personal attributes = changed
              ↓
Score = unchanged
Matching factors = unchanged
Ranking = unaffected
```

Any unexpected change must be treated as a fairness defect.

---

## 19. Evaluation Dataset

The evaluation dataset should contain approximately:

* 100 synthetic or anonymized/consented resumes
* Multiple representative job descriptions

No unconsented real candidate resumes may be used.

At least two human evaluators should independently label:

* Relevant skills
* Required/preferred skill classification
* Candidate-job relevance
* Human shortlist

Disagreements should be resolved before the labels are used. Because the dataset is small, results are indicative rather than statistically conclusive.

---

## 20. Persistence

Completed analysis results must persist so that recruiters can:

* Return to previous analyses.
* View candidate rankings and details.
* Review AI explanations.
* Delete saved analysis results.

Raw resume files follow the retention policy in Section 13.

---

## 21. MVP UI Requirements

### Job Description

* Upload or paste JD
* View, edit, and manually add extracted requirements

### Resume Upload

* Multiple resume upload
* File validation
* Upload progress/status
* Failed-file reporting
* Duplicate detection feedback

### Analysis

* Analyze button
* Processing status
* Partial-failure status

### Results

* Ranked candidate list with match score and score breakdown
* Per-candidate details as listed in Section 10
* AI-generated explanation, strengths, and gaps

### Saved Analyses

* View previous analyses
* Delete saved analyses

---

## 22. Out of Scope

The MVP will not include:

* Candidate login
* Recruiter authentication
* Candidate applications
* Job portal
* Interview scheduling
* Email automation
* WhatsApp integration
* Payments
* Mobile application
* General-purpose chatbot
* LLM fine-tuning
* Custom LLM training
* Multi-agent architecture
* Automatic hiring decisions

---

## 23. Success Criteria

The MVP is successful when a recruiter can:

1. Provide a job description.
2. Review and correct extracted job requirements.
3. Upload multiple resumes.
4. Successfully process valid documents.
5. Identify failed documents without stopping the entire analysis.
6. Identify required and preferred skills.
7. Normalize equivalent skill names.
8. Identify candidate skills, experience, projects, and education.
9. Compare candidates using semantic relevance and structured matching factors.
10. Calculate explainable candidate scores.
11. Rank candidates deterministically.
12. Inspect the evidence behind a candidate's ranking.
13. Generate grounded AI explanations.
14. Return to previously saved analyses.
15. Delete saved analysis results.
16. Meet the quality, performance, and fairness targets in Sections 16–18.
