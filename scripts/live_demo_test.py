"""
Live End-to-End System Test with Sample Resumes.
Executes against the running FastAPI server (http://localhost:8000) and Celery Worker.
"""

import io
import os
import sys
import time

import docx
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8000/api"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def build_candidate_docx(name: str, email: str, title: str, years: int, skills: list[str], bio: str) -> bytes:
    """Builds a rich, realistic candidate DOCX file."""
    doc = docx.Document()
    doc.add_heading(name, level=0)
    doc.add_paragraph(f"{email} | +1 (555) 014-9982 | San Francisco, CA")

    doc.add_heading("Professional Summary", level=1)
    doc.add_paragraph(bio)

    doc.add_heading("Core Technical Competencies", level=1)
    doc.add_paragraph(", ".join(skills))

    doc.add_heading("Work Experience", level=1)
    doc.add_paragraph(f"{title} | CloudScale Technologies (2020 - Present)")
    doc.add_paragraph(
        f"- Architected distributed backend APIs and microservices using {skills[0]} and {skills[1] if len(skills)>1 else 'SQL'}.\n"
        f"- Managed production databases and optimized high-throughput queries with {skills[2] if len(skills)>2 else 'PostgreSQL'}.\n"
        f"- Automated CI/CD deployment pipelines using Docker containers and cloud infrastructure."
    )

    doc.add_paragraph(f"Software Developer | NextGen Systems (2018 - 2020)")
    doc.add_paragraph(
        "- Contributed to frontend features and backend integration endpoints.\n"
        "- Collaborated with QA and product engineers in an Agile sprint environment."
    )

    doc.add_heading("Education", level=1)
    doc.add_paragraph("Bachelor of Science in Computer Science | California State University")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def run_live_test():
    print("=" * 75)
    print("  LIVE RESUME ANALYZER DEMONSTRATION & END-TO-END PIPELINE TEST")
    print("=" * 75)
    print(f"Target Server: {BASE_URL}")

    client = httpx.Client(timeout=30.0)

    # 1. Health check
    try:
        health_resp = client.get(f"{BASE_URL}/health")
        print(f"\n[1/7] Checking Live Backend Health: HTTP {health_resp.status_code}")
        print(f"      Response: {health_resp.json()}")
    except Exception as e:
        print(f"ERROR: Cannot connect to {BASE_URL}. Ensure FastAPI is running! Details: {e}")
        return

    # 2. Create Analysis
    print("\n[2/7] Creating New Job Analysis...")
    jd_content = (
        "Position: Senior Full-Stack Engineer\n\n"
        "About the Role:\n"
        "We are seeking an experienced Senior Full-Stack Engineer to lead the design and "
        "development of high-performance web applications and scalable microservices.\n\n"
        "Core Required Qualifications:\n"
        "- 4+ years of software development experience\n"
        "- High proficiency with Python, FastAPI, and PostgreSQL\n"
        "- Solid understanding of database design, indexing, and RESTful architectures\n\n"
        "Preferred Qualifications:\n"
        "- Experience with Docker containerization and Redis caching\n"
        "- Experience building modern reactive frontends with React or TypeScript\n"
        "- Familiarity with asynchronous task queues and cloud systems\n"
    )

    create_resp = client.post(
        f"{BASE_URL}/analyses",
        data={"name": "Senior Full-Stack Engineer (Live Demo)", "jd_text": jd_content},
    )
    assert create_resp.status_code == 201, f"Failed to create analysis: {create_resp.text}"
    analysis = create_resp.json()["analysis"]
    analysis_id = analysis["id"]
    print(f"      Created Analysis ID: {analysis_id}")
    print(f"      Status: {analysis['status']}")

    # 3. Inspect and Confirm Requirements
    print("\n[3/7] Reviewing Extracted Job Requirements...")
    reqs_resp = client.get(f"{BASE_URL}/analyses/{analysis_id}/requirements")
    reqs = reqs_resp.json()
    print(f"      Required Skills Identified: {reqs['required_skills']}")
    print(f"      Preferred Skills Identified: {reqs['preferred_skills']}")
    print(f"      Experience Criteria: {reqs['experience_requirements']}")

    confirm_resp = client.post(f"{BASE_URL}/analyses/{analysis_id}/requirements/confirm")
    assert confirm_resp.status_code == 200, f"Failed to confirm requirements: {confirm_resp.text}"
    print(f"      Requirements Confirmed At: {confirm_resp.json()['confirmed_at']}")

    # 4. Generate & Upload 4 Sample Candidates
    print("\n[4/7] Generating and Uploading 4 Realistic Candidate Resumes (.docx)...")
    candidates_meta = [
        {
            "filename": "Alex_Rivera_Resume.docx",
            "name": "Alex Rivera",
            "email": "alex.rivera@example.com",
            "title": "Senior Backend Engineer",
            "years": 6,
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "React"],
            "bio": "Senior Backend Engineer with 6 years of expertise building resilient Python and FastAPI microservices with PostgreSQL and Docker.",
        },
        {
            "filename": "Jordan_Hayes_Resume.docx",
            "name": "Jordan Hayes",
            "email": "jordan.hayes@example.com",
            "title": "Full Stack Engineer",
            "years": 4,
            "skills": ["Python", "PostgreSQL", "Docker", "React", "TypeScript"],
            "bio": "Full Stack Engineer with 4 years of experience delivering end-to-end features with Python, PostgreSQL, and React frontends.",
        },
        {
            "filename": "Taylor_Bennett_Resume.docx",
            "name": "Taylor Bennett",
            "email": "taylor.bennett@example.com",
            "title": "Junior Python Developer",
            "years": 2,
            "skills": ["Python", "Flask", "SQLite", "Git"],
            "bio": "Junior Python Developer with 2 years experience building internal REST APIs with Flask and relational databases.",
        },
        {
            "filename": "Morgan_Casey_Resume.docx",
            "name": "Morgan Casey",
            "email": "morgan.casey@example.com",
            "title": "Java Systems Engineer",
            "years": 5,
            "skills": ["Java", "Spring Boot", "MySQL", "Kubernetes", "Kafka"],
            "bio": "Java backend developer with 5 years experience designing enterprise services using Spring Boot and MySQL.",
        },
    ]

    files_payload = []
    for c in candidates_meta:
        b = build_candidate_docx(c["name"], c["email"], c["title"], c["years"], c["skills"], c["bio"])
        files_payload.append(("files", (c["filename"], b, DOCX_MIME)))

    upload_resp = client.post(f"{BASE_URL}/analyses/{analysis_id}/resumes", files=files_payload)
    assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
    upload_data = upload_resp.json()
    print(f"      Upload Accepted Count: {upload_data['accepted_count']}")
    for item in upload_data["results"]:
        print(f"      - {item['filename']}: Status = {item['status']}")

    # 5. Start Live Background Analysis
    print("\n[5/7] Starting Live Asynchronous Background Pipeline...")
    start_resp = client.post(f"{BASE_URL}/analyses/{analysis_id}/start")
    assert start_resp.status_code == 200
    print(f"      Analysis State: {start_resp.json()['status']}")
    print("      Waiting for Celery worker to extract, embed, score, and rank candidates...")

    # Poll status
    t_start = time.perf_counter()
    timeout_seconds = 30.0
    final_status = None

    while time.perf_counter() - t_start < timeout_seconds:
        status_resp = client.get(f"{BASE_URL}/analyses/{analysis_id}/status")
        status_data = status_resp.json()
        curr_state = status_data["status"]
        processed = status_data["processed"]
        total = status_data["total"]

        print(f"      [Progress] Status: {curr_state} | Processed: {processed}/{total} (Elapsed: {time.perf_counter() - t_start:.1f}s)")

        if curr_state == "RANKED":
            final_status = status_data
            break
        elif curr_state == "FAILED":
            print(f"ERROR: Analysis marked FAILED: {status_data.get('failure_reason')}")
            return

        time.sleep(1.0)

    if not final_status:
        print("ERROR: Timed out waiting for analysis to reach RANKED status.")
        return

    duration = time.perf_counter() - t_start
    print(f"      >> Successfully finalized & ranked in {duration:.2f} seconds!")

    # 6. Retrieve Candidate Rankings Leaderboard
    print("\n[6/7] Retrieving Candidate Leaderboard & Breakdown...")
    cand_resp = client.get(f"{BASE_URL}/analyses/{analysis_id}/candidates")
    ranking = cand_resp.json()["ranking"]

    print("\n" + "=" * 80)
    print(f"{'RANK':<5} | {'ANONYMOUS LABEL':<16} | {'MATCH SCORE':<12} | {'REQ SKILLS':<12} | {'EXPERIENCE'}")
    print("-" * 80)
    for c in ranking:
        rank = c["rank"]
        label = c["label"]
        score = f"{c['match_score']:.1f}/100"
        req_cov = f"{c['required_skill_coverage']['value']:.1f}%" if c['required_skill_coverage']['value'] is not None else "N/A"
        exp_cov = f"{c['relevant_experience']['value']:.1f}%" if c['relevant_experience']['value'] is not None else "N/A"
        print(f"{rank:<5} | {label:<16} | {score:<12} | {req_cov:<12} | {exp_cov}")
    print("=" * 80)

    # 7. Request and View AI Explanation for Rank 1
    top_candidate = ranking[0]
    top_cand_id = top_candidate["candidate_id"]
    print(f"\n[7/7] Requesting AI Explanation for Rank 1 ({top_candidate['label']})...")

    expl_req = client.post(f"{BASE_URL}/analyses/{analysis_id}/candidates/{top_cand_id}/explanation")
    print(f"      Requested Explanation: State = {expl_req.json()['state']}")

    # Poll explanation state
    t_expl_start = time.perf_counter()
    ready_explanation = None
    while time.perf_counter() - t_expl_start < 15.0:
        expl_get = client.get(f"{BASE_URL}/analyses/{analysis_id}/candidates/{top_cand_id}/explanation")
        expl_res = expl_get.json()
        if expl_res["state"] == "READY":
            ready_explanation = expl_res["explanation"]
            break
        elif expl_res["state"] == "FAILED":
            print(f"      Explanation marked FAILED: {expl_res.get('failure_reason')}")
            break
        time.sleep(1.0)

    if ready_explanation:
        print("\n  >>> AI Generated Grounded Explanation:")
        print(f"      - Strengths: {ready_explanation.get('strengths')}")
        print(f"      - Gaps: {ready_explanation.get('gaps')}")
        print(f"      - Experience Alignment: {ready_explanation.get('experience_alignment')}")
        print(f"      - Assessment: {ready_explanation.get('assessment')}")
    else:
        print("      Explanation generation was queued for background inference.")

    print("\n" + "=" * 75)
    print("  LIVE DEMO TEST COMPLETE!")
    print(f"  You can now open http://localhost:5173 in Chrome to view this exact")
    print(f"  analysis ('Senior Full-Stack Engineer (Live Demo)') on your screen!")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_live_test()
