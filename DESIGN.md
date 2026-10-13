# DESIGN.md

# Design System — AI Resume Analyzer & Job Matching System

## 1. Design Goal

The interface should feel like a professional recruiter/HR analytics application.

It should communicate that it is:

* Professional
* Trustworthy
* Clear
* Data-focused
* Minimal
* Easy to scan

The UI prioritizes recruiter productivity over visual decoration. It must not look like a generic AI chatbot.

---

## 2. Design Principles

### 2.1 Clarity First

Recruiters should immediately understand:

* Which analysis they are viewing and what stage it is in
* How many resumes were processed, failed, or need review
* Which candidates ranked highest and why
* Which requirements are missing
* Whether an AI explanation is available

Avoid unnecessary visual elements.

### 2.2 Information Hierarchy

Important information has stronger visual emphasis. Priority order:

1. Candidate ranking / score
2. Required skill coverage
3. Relevant experience
4. Candidate-job alignment
5. Preferred skills
6. Education / explicit requirements
7. Detailed supporting information

### 2.3 Evidence Before AI

Matching results are visually primary. AI-generated explanations support the matching results and never dominate the interface.

### 2.4 Consistency

Use the same typography, colors, spacing, buttons, cards, badges, tables, form controls, and status indicators throughout the application.

### 2.5 Accessibility

All important interactions must support keyboard navigation, visible focus states, sufficient color contrast, clear labels, and screen readers where practical. Status is never communicated by color alone.

---

## 3. Visual Style

Modern, minimal, professional, enterprise-oriented, with clean whitespace, subtle borders, and limited decoration.

Avoid:

* Excessive gradients
* Glassmorphism
* Large illustrations
* Excessive animation
* Neon colors
* Chatbot-style layouts
* Heavily rounded elements

---

## 4. Typography

**Primary font:** `Inter`

**Fallback:** `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`

Scale:

* Page title: 28px, weight 700, line height 1.2
* Section heading: 20px, weight 600
* Card heading: 16px, weight 600
* Body: 14–16px, weight 400, line height 1.5
* Supporting text: 13–14px, weight 400
* Table text: 13–14px

Avoid using too many font sizes.

---

## 5. Color System

A neutral professional interface with one primary accent.

```text
Primary:            #4F46E5
Primary Hover:      #4338CA
Primary Light:      #EEF2FF

Page Background:    #F8FAFC
Surface:            #FFFFFF
Secondary Surface:  #F1F5F9

Primary Text:       #0F172A
Secondary Text:     #475569
Muted Text:         #64748B
Disabled Text:      #94A3B8

Border:             #E2E8F0
Border Strong:      #CBD5E1
```

Semantic colors:

```text
Success:  #16A34A   Background: #F0FDF4
Warning:  #D97706   Background: #FFFBEB
Error:    #DC2626   Background: #FEF2F2
Info:     #2563EB   Background: #EFF6FF
```

Do not communicate meaning through color alone.

---

## 6. Layout

### Desktop

A two-part application shell: top header, sidebar, and main content.

```text
┌──────────────────────────────────────────────────────────┐
│ Top Header                                               │
├──────────────┬───────────────────────────────────────────┤
│   Sidebar    │              Main Content                 │
└──────────────┴───────────────────────────────────────────┘
```

The sidebar contains:

* Dashboard
* New Analysis
* Saved Analyses

The main content area is centered with a maximum width of `1280px` and consistent horizontal and vertical spacing.

### Spacing

Use multiples of 4px: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64.

* Small: 8px
* Medium: 16px
* Large: 24px
* Section: 32px

Avoid arbitrary spacing values.

### Border radius

* Small controls: 6px
* Inputs and buttons: 8px
* Cards: 10px
* Large containers: 12px

### Shadows

Prefer borders (`1px solid #E2E8F0`) over shadows. Use subtle shadows only for dropdowns, modals, and floating elements.

---

## 7. Buttons

**Primary:** the main action on a screen. Primary background, white text, 8px radius, medium weight. Examples: Continue, Confirm Requirements, Start Analysis, Generate AI Explanation.

**Secondary:** supporting actions. White background, border, dark text. Examples: Cancel, Edit Requirements, View Details.

**Destructive:** irreversible actions only, in the error color with clear wording. Example: Delete Analysis.

Do not use destructive styling for normal actions.

---

## 8. Forms

Forms use visible labels, helpful descriptions where needed, clear validation messages close to the affected field, consistent input heights, and keyboard-accessible controls.

---

## 9. Reusable Components

Create reusable components for:

* Button, Input, Textarea
* FileUpload
* Badge, StatusBadge
* Card, Modal
* ProgressBar, ScoreDisplay
* DataTable
* EmptyState, ErrorState, LoadingState
* RequirementChip, SkillBadge

Do not create visually different versions of the same component for individual pages.

---

## 10. Application Flow

```text
Create Analysis (JD)
      ↓
Review Requirements
      ↓
Upload Resumes
      ↓
Start Analysis
      ↓
Processing
      ↓
Ranked Results
      ↓
Candidate Details
      ↓
Optional AI Explanation
```

The Ranked Results screen is the most important screen in the application.

### Analysis statuses

* **Pending** — requirements review and resume upload are still in progress.
* **Processing** — resumes are being analyzed.
* **Ranked** — ranking is available.
* **Failed** — an unrecoverable system-level error occurred.

### Opening a saved analysis

* **Pending:** reopens at the requirements or upload step, whichever is incomplete.
* **Processing:** opens the processing screen.
* **Ranked:** opens the results screen.
* **Failed:** opens an error screen explaining what happened.

### Rules tied to the backend lifecycle

* Resume upload is allowed only while the analysis is Pending.
* After Start Analysis, uploads and requirement edits are locked.
* Ranking appears without waiting for any AI explanation.

---

## 11. Dashboard

Gives a quick overview of previous analyses and access to a new analysis.

```text
Dashboard                                  [ + New Analysis ]

Recent Analyses
────────────────────────────────────────────────────────────
Analysis Name       Candidates   Status       Updated
Backend Engineer    24           Ranked       Oct 10
Frontend Intern     18           Ranked       Oct 08
Data Analyst        12           Failed       Oct 05
```

Each row is clickable and shows the analysis name, candidate count, status, and last-updated date. The analysis name defaults from the job title or file name and can be edited when the analysis is created.

---

## 12. Job Description Screen

The recruiter uploads a JD or pastes the text.

```text
Create Analysis

Job Description

[ Upload JD ]    or    [ Paste Job Description ]

Supported formats: PDF, DOCX

                                          [ Continue ]
```

---

## 13. Requirement Review Screen

An important confirmation step. Extracted requirements are shown in groups and every requirement is editable.

```text
Review Job Requirements

Required Skills
[ Python ] [ FastAPI ] [ PostgreSQL ]   [ + Add ]

Preferred Skills
[ Docker ] [ AWS ]                      [ + Add ]

Experience
2+ years

Education
Bachelor's degree

Other Requirements
...

                                [ Confirm Requirements ]
```

### When requirements cannot be identified

If the system cannot reliably identify requirements:

```text
We couldn't identify the job requirements.
Please add them manually to continue.
```

The requirement groups are shown empty and editable, and Confirm Requirements stays disabled until sufficient criteria are present.

Confirming requirements saves them and moves to resume upload. It does not start processing.

---

## 13.1 Resume Upload Screen

The interface supports multiple files, up to 50 accepted resumes. Duplicates and rejected files do not count toward the limit.

```text
Upload Resumes

┌─────────────────────────────────────────────┐
│       Drag & drop resumes here              │
│          or [ Browse Files ]                │
│      PDF / DOCX • Max 10MB each             │
└─────────────────────────────────────────────┘

Selected Files

resume_01.pdf     PDF    1.2 MB    Ready
resume_02.docx    DOCX   0.8 MB    Ready
resume_03.pdf     PDF    1.2 MB    Duplicate
resume_04.txt     TXT    0.1 MB    Unsupported format

                                  [ Start Analysis ]
```

Each file shows its name, type, size, and status:

* **Ready** — accepted and registered.
* **Duplicate** — identical content was already uploaded in this analysis. It is excluded and clearly labeled.
* **Unsupported format** or **Too large** — rejected at upload, with the reason.
* **Limit reached** — the analysis already has 50 accepted resumes, so this file was not accepted.
* **Expired** — the uploaded file was removed after the retention window. The recruiter is asked to upload it again.

Files are uploaded in small batches so that each file shows its own progress and status.

Start Analysis is enabled once requirements are confirmed and at least one resume is Ready. Starting is final: uploads and requirement edits are then locked.

Problems found during extraction (corrupted, scanned, unreliable layout) are reported on the processing screen, since they are only discovered once analysis begins.

---

## 14. Processing Screen

Processing shows progress and does not pretend to be one synchronous action.

```text
Analyzing Candidates

18 resumes in this analysis
2 duplicates excluded

Processed 15 of 18

███████████████░░░░░ 83%

Completed       12
Needs review     1
Failed           2
Remaining        3
```

Counts on this screen refer to analyzed resumes only, meaning files that were Ready when the analysis started. Duplicates and files rejected at upload are excluded and reported separately.

Failed and needs-review files are listed separately, with the reason:

```text
2 files could not be processed

resume_08.pdf
Scanned/image-only document. Upload a text-based PDF or DOCX.

resume_19.pdf
Corrupted file. Upload a valid document.

1 file needs review

resume_14.docx
The structure could not be reliably analyzed.
```

A failed or needs-review resume never appears as a low-scoring candidate. It is not ranked, and it is shown in its own section on the results screen as well.

When processing finishes, the recruiter is taken to the ranked results.

---

## 15. Results / Ranking Screen

The primary application screen.

Header:

```text
Backend Engineer

20 files uploaded • 2 duplicates excluded
18 analyzed: 15 ranked • 2 failed • 1 needs review

[ View Requirements ]
```

Ranking table:

```text
Rank  Candidate     Score  Required Skills  Experience  Actions
────────────────────────────────────────────────────────────────
1     Candidate 01  92%    100%             Strong      View
2     Candidate 07  87%     90%             Strong      View
3     Candidate 03  81%     80%             Moderate    View
```

The ranking shows candidates by system-generated labels only. Names and contact details are not shown in the ranking table. Labels are assigned once when ranking finishes and stay the same whenever the analysis is reopened.

Below the table, a separate section lists failed and needs-review files with reasons.

---

## 16. Score Display

Scores are visually prominent but not misleading.

```text
92%
Match Score

Required Skills       100%
Preferred Skills       80%
Relevant Experience    90%
Semantic Relevance     91%
Education              Meets requirement
```

Use a progress indicator or compact visualization.

### Components that do not apply

If the job did not specify a requirement, show that instead of a check, cross, or percentage:

* No preferred skills in the job → "No preferred skills specified"
* No education requirement → "Not specified in job"
* A component that could not be determined → "Could not be determined"

This makes clear that unspecified requirements did not affect the score.

### Wording

Use: Match Score, Matching Assessment, Candidate-Job Alignment.

Avoid: Hire, Reject, Best Employee, Guaranteed Fit.

The score must never look like a hiring decision.

---

## 17. Candidate Detail Screen

```text
Candidate 01

Match Score
92%

────────────────────────────────

Candidate Information
Name:         ...
Contact:      ...

────────────────────────────────

Required Skills
✓ Python   ✓ FastAPI   ✓ PostgreSQL   ✕ AWS

Preferred Skills
✓ Docker   ✕ Kubernetes

Relevant Experience
2.5 years

Education
Meets requirement

────────────────────────────────

Experience Alignment
...

[ Generate AI Explanation ]
```

### Identity

The ranking is shown without names. Name and contact details are revealed only on the candidate detail screen, so the recruiter can still identify and contact the candidate.

### Evidence

The recruiter must be able to understand the score without requesting an AI explanation. Evidence includes:

* Matched required and preferred skills
* Missing required and preferred skills
* Concise extracted evidence for relevant experience

### Original resume

Original resume files are deleted after the extraction attempt and cannot be viewed in the application. Candidate details and matching evidence are based on extracted structured data. Raw resume text is never displayed.

---

## 18. AI Explanation

An on-demand action, clearly labeled as AI-generated.

```text
[ Generate AI Explanation ]
```

After generation:

```text
AI Assessment

Strengths
- Strong backend experience
- Covers all core required skills

Gaps
- AWS experience not identified

Experience Alignment
Candidate experience aligns with the backend
responsibilities described in the job requirements.
```

The explanation is never presented as the source of the numerical score. A failed explanation can be retried, but a successful explanation cannot be regenerated in the MVP.

### Explanation states

* **Not requested:** shows `[ Generate AI Explanation ]`.
* **Generating:** shows "Generating explanation... This may take a few seconds." The button is disabled so a second request cannot start. If the recruiter leaves and returns, the generating state is still shown and updates when ready.
* **Ready:** shows the explanation.
* **Failed:**

```text
We couldn't generate the explanation.
The matching results are still available.

[ Try Again ]
```

A failed explanation never affects the candidate's ranking or score.

---

## 19. Saved Analyses

A simple table or card list showing name, candidate count, status, and date. Actions: Open, Delete.

```text
Saved Analyses

Backend Engineer     20 candidates    Ranked    Oct 10, 2026    [ Open ] [ Delete ]
Frontend Developer   15 candidates    Ranked    Oct 08, 2026    [ Open ] [ Delete ]
```

Deletion requires confirmation:

```text
Delete this analysis?

This will permanently remove the saved analysis
and its associated candidate matching data.

[ Cancel ]  [ Delete Analysis ]
```

Delete is available for Pending, Ranked, and Failed analyses. It is disabled while an analysis is Processing, with a short explanation that it can be deleted once processing finishes.

After the recruiter confirms deletion, the analysis disappears from the list immediately. Cleanup of the remaining data continues in the background, and no deletion-in-progress state is shown.

---

## 20. Status Indicators

Every status shows both color and text or an icon.

* **Analysis:** Pending, Processing, Ranked, Failed
* **Resume file:** Ready, Duplicate, Unsupported format, Too large, Limit reached, Expired, Failed, Needs review
* **Explanation:** Not Requested, Generating, Ready, Failed

---

## 21. Loading, Empty, and Error States

### Loading

Every asynchronous operation has a loading state: button spinners, skeleton table rows, progress indicators, or loading text. Avoid blank screens while data loads.

### Empty

Empty states explain what to do next.

```text
No analyses yet

Create your first resume analysis to compare
candidates against a job description.

[ + New Analysis ]
```

### Error

Errors are specific, understandable, and actionable. Do not expose stack traces or internal details.

Bad: `Something went wrong.`

Better:

```text
The resume could not be processed because the
document contains no reliably extractable text.

Please upload a text-based PDF or DOCX file.
```

An error never causes unrelated parts of the screen to disappear.

---

## 22. Responsive Design

The application must work at:

* Mobile: 375px and up
* Tablet: 768px and up
* Desktop: 1440px and up

**Mobile:** the sidebar collapses into a menu button (☰) that reveals the same navigation options. Large tables become scrollable tables, stacked candidate cards, or responsive detail views. Do not simply shrink desktop tables until they are unreadable.

**Tablet:** a compact sidebar and responsive content width.

**Desktop:** the full layout with sidebar and data tables.

---

## 23. Accessibility

All interactive elements have a visible focus state, an accessible label, keyboard support, and appropriate semantic HTML.

* Forms have associated labels.
* Buttons describe their action.
* Icons are never the only indication of meaning.
* Modal dialogs trap focus appropriately, provide a clear close action, and are keyboard accessible.

---

## 24. Tables, Visualization, Icons, and Notifications

### Tables

* Clear column headers
* Horizontal scrolling when necessary
* Important columns stay visible
* Candidate and text columns left-aligned, scores centered or right-aligned, actions right-aligned
* Avoid excessive borders

### Data visualization

Keep it simple: score progress bars, skill coverage indicators, processing progress, and small summary statistics. Avoid pie charts for every metric and dashboards full of charts. This is a candidate comparison tool, not an analytics platform.

### Icons

Use icons sparingly and from one consistent library. Icons support text and do not replace it.

### Notifications

Use non-blocking notifications for successful actions, such as "Requirements confirmed." and "Analysis deleted successfully." Errors that need action appear near the relevant UI. Avoid excessive toasts.

---

## 24.1 Interaction Rules

* **Destructive actions** always require confirmation.
* **Long operations** always show progress or status.
* **Duplicate actions** are disabled while the same operation is running.
* **Navigation:** users can return to saved analyses without losing completed results.

---

## 25. Design Language

The application should feel like a professional recruitment analysis and decision-support platform. It emphasizes trust, evidence, comparison, and clarity.

It should not feel like a chatbot, a social media application, a consumer AI toy, a generic admin template, or a flashy AI landing page.

---

## 26. Design Constraints

The frontend must:

1. Follow this design system and use reusable components.
2. Maintain consistent spacing and typography and responsive layouts.
3. Provide loading, empty, and error states.
4. Provide accessible forms.
5. Follow the lifecycle rules in Section 10, including the explicit Start Analysis step.
6. Show duplicate, failed, and needs-review files clearly and never rank them.
7. Clearly distinguish matching results from AI-generated explanations.
8. Never present AI explanations as the numerical scoring mechanism.
9. Show candidate names and contact details only on the detail screen.
10. Show "not specified" for requirements the job did not state.
11. Keep candidate comparison fast and easy to scan.
