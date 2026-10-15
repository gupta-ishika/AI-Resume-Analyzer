"""
Generates 10 distinct, professional PDF resumes calibrated across different match score tiers,
and executes a live end-to-end analysis against the running backend and UI.
"""

import io
import os
import sys
import time

import httpx
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8000/api"
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample_resumes"))

# ----------------------------------------------------------------------
# 1. JOB DESCRIPTION
# ----------------------------------------------------------------------
JOB_NAME = "Senior Backend Platform Engineer"
JOB_DESCRIPTION = """Position: Senior Backend Platform Engineer
Company: CloudScale Infrastructure Systems
Location: Remote / San Francisco, CA

About the Opportunity:
We are seeking an experienced Senior Backend Platform Engineer to lead the architecture,
development, and operational scaling of our distributed microservices platform.

Core Required Qualifications:
- 5+ years of professional backend software development experience
- High proficiency with Python, FastAPI, and PostgreSQL
- Strong hands-on experience with Docker containerization and Redis caching
- Deep understanding of REST APIs, database indexing, and microservices architecture

Preferred Qualifications:
- Experience with AWS cloud infrastructure and Kubernetes orchestration
- Experience with CI/CD deployment automation and Git version control
- Bachelor's or Master's degree in Computer Science or related technical discipline
"""

# ----------------------------------------------------------------------
# 2. 10 CANDIDATE PROFILES CALIBRATED FOR DIFFERENT SCORES
# ----------------------------------------------------------------------
CANDIDATE_DATA = [
    {
        "filename": "01_Elena_Vance_Tier1_95pct.pdf",
        "name": "Elena Vance",
        "email": "elena.vance@example.com",
        "phone": "+1 (555) 011-8492",
        "title": "Principal Backend Systems Architect",
        "years": 7.0,
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "REST APIs", "Microservices", "AWS", "Kubernetes", "Git"],
        "degree": "Master of Science in Computer Science, Carnegie Mellon University",
        "summary": "Accomplished Backend Systems Architect with 7 years of specialized expertise in Python, FastAPI microservices, high-throughput PostgreSQL databases, Docker containerization, and AWS Kubernetes infrastructure.",
        "experience": [
            ("Lead Backend Engineer | Apex Distributed Cloud (2021 - Present)",
             "Architected mission-critical distributed microservices in Python and FastAPI serving 25k RPS. Optimized PostgreSQL connection pooling and Redis multi-tier caching clusters on AWS."),
            ("Senior Backend Developer | DataMesh Systems (2018 - 2021)",
             "Implemented containerized services using Docker and automated Kubernetes deployment manifests. Built robust REST APIs with asynchronous task execution.")
        ]
    },
    {
        "filename": "02_Marcus_Thorne_Tier2_85pct.pdf",
        "name": "Marcus Thorne",
        "email": "marcus.thorne@example.com",
        "phone": "+1 (555) 012-7731",
        "title": "Senior Backend Developer",
        "years": 5.5,
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "REST APIs", "Microservices", "Git"],
        "degree": "Bachelor of Science in Computer Engineering, University of Washington",
        "summary": "Senior Backend Developer with 5.5 years experience designing scalable Python and FastAPI services, managing relational data in PostgreSQL, and deploying via Docker containers.",
        "experience": [
            ("Senior Backend Developer | ScaleWorks Technologies (2021 - Present)",
             "Developed core microservices and REST APIs using FastAPI, PostgreSQL, and Redis caching. Containerized application dependencies using Docker."),
            ("Backend Software Engineer | CloudStack Inc (2019 - 2021)",
             "Maintained REST API endpoints in Python, wrote unit tests in Git CI pipelines, and improved database query execution times.")
        ]
    },
    {
        "filename": "03_Chloe_Zhao_Tier3_75pct.pdf",
        "name": "Chloe Zhao",
        "email": "chloe.zhao@example.com",
        "phone": "+1 (555) 013-6624",
        "title": "Backend Software Engineer",
        "years": 4.5,
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "REST APIs", "Git"],
        "degree": "Bachelor of Science in Computer Science, UC San Diego",
        "summary": "Backend Software Engineer with 4.5 years of experience developing REST APIs in Python and FastAPI with PostgreSQL databases and Docker containers.",
        "experience": [
            ("Backend Engineer | FinTech Innovations (2022 - Present)",
             "Engineered transaction ingestion services using FastAPI and PostgreSQL with Docker deployments."),
            ("Software Developer | AlphaLabs (2020 - 2022)",
             "Maintained backend endpoints in Python, authored integration tests, and managed version control in Git.")
        ]
    },
    {
        "filename": "04_Liam_Gallagher_Tier4_68pct.pdf",
        "name": "Liam Gallagher",
        "email": "liam.gallagher@example.com",
        "phone": "+1 (555) 014-5519",
        "title": "Python Backend Engineer",
        "years": 5.0,
        "skills": ["Python", "Django", "PostgreSQL", "Redis", "Docker", "Git", "REST APIs"],
        "degree": "Bachelor of Science in Information Technology, Purdue University",
        "summary": "Python Developer with 5 years experience building web applications and REST APIs using Django, PostgreSQL, and Redis caching with Docker.",
        "experience": [
            ("Python Developer | Enterprise Solutions Corp (2021 - Present)",
             "Architected customer-facing web services using Python, Django REST framework, and PostgreSQL. Configured Redis cache keys to reduce database load."),
            ("Application Developer | TechCore Labs (2019 - 2021)",
             "Built monolithic REST endpoints in Django with Docker environments.")
        ]
    },
    {
        "filename": "05_Sofia_Ramos_Tier5_60pct.pdf",
        "name": "Sofia Ramos",
        "email": "sofia.ramos@example.com",
        "phone": "+1 (555) 015-4428",
        "title": "Software Engineer",
        "years": 3.5,
        "skills": ["Python", "Flask", "SQL", "Docker", "Git", "REST APIs"],
        "degree": "Bachelor of Science in Computer Science, Arizona State University",
        "summary": "Software Engineer with 3.5 years experience implementing microservices and REST APIs using Python, Flask, and relational SQL databases.",
        "experience": [
            ("Software Engineer | NextGen Apps (2022 - Present)",
             "Implemented backend API services using Python and Flask. Created Docker build configs and optimized SQL queries."),
            ("Junior Developer | CodeCrafters (2021 - 2022)",
             "Built REST API endpoints and maintained database integration in Python.")
        ]
    },
    {
        "filename": "06_David_Kim_Tier6_50pct.pdf",
        "name": "David Kim",
        "email": "david.kim@example.com",
        "phone": "+1 (555) 016-3391",
        "title": "Full Stack Developer",
        "years": 4.0,
        "skills": ["JavaScript", "TypeScript", "React", "Python", "PostgreSQL", "Node.js", "Git"],
        "degree": "Bachelor of Science in Software Engineering, UT Austin",
        "summary": "Full Stack Developer with 4 years experience creating React frontend applications with secondary experience building Python and Node.js backend services on PostgreSQL.",
        "experience": [
            ("Full Stack Developer | OmniTech Systems (2021 - Present)",
             "Built responsive React user interfaces and connected them to Node.js and Python backend endpoints with PostgreSQL."),
            ("Frontend Developer | WebVenture (2020 - 2021)",
             "Implemented user workflows using TypeScript and React.")
        ]
    },
    {
        "filename": "07_Aisha_Patel_Tier7_40pct.pdf",
        "name": "Aisha Patel",
        "email": "aisha.patel@example.com",
        "phone": "+1 (555) 017-2284",
        "title": "Junior Python Developer",
        "years": 2.0,
        "skills": ["Python", "SQLite", "Git", "HTML5", "CSS"],
        "degree": "Associate Degree in Computer Programming, City College",
        "summary": "Junior Python Developer with 2 years practical experience writing automation scripts and basic database queries in Python and SQLite.",
        "experience": [
            ("Junior Developer | TechLaunch Studio (2022 - Present)",
             "Assisted in developing internal utilities and data formatting scripts using Python and Git."),
            ("Intern | ByteForge (2021 - 2022)",
             "Wrote unit tests and basic SQLite database schema updates.")
        ]
    },
    {
        "filename": "08_Carlos_Mendez_Tier8_32pct.pdf",
        "name": "Carlos Mendez",
        "email": "carlos.mendez@example.com",
        "phone": "+1 (555) 018-1175",
        "title": "DevOps & Cloud Systems Engineer",
        "years": 4.0,
        "skills": ["Docker", "Kubernetes", "Linux", "AWS", "Git"],
        "degree": "Bachelor of Science in Network Engineering, Florida Tech",
        "summary": "DevOps Engineer with 4 years hands-on experience provisioning AWS infrastructure, Docker container clusters, and Kubernetes deployments.",
        "experience": [
            ("DevOps Engineer | CloudVantage (2021 - Present)",
             "Administered multi-region AWS Kubernetes clusters, managed Docker base images, and maintained CI/CD runners in Linux."),
            ("Systems Administrator | NetGrid Corp (2020 - 2021)",
             "Configured Linux servers and automated shell deployments.")
        ]
    },
    {
        "filename": "09_Viktor_Hansen_Tier9_25pct.pdf",
        "name": "Viktor Hansen",
        "email": "viktor.hansen@example.com",
        "phone": "+1 (555) 019-0062",
        "title": "Java Enterprise Backend Engineer",
        "years": 5.0,
        "skills": ["Java", "Spring Boot", "MySQL", "Kafka", "Git"],
        "degree": "Bachelor of Science in Computer Science, University of Illinois",
        "summary": "Enterprise Java Developer with 5 years experience architecting backend microservices in Java and Spring Boot with MySQL and Apache Kafka.",
        "experience": [
            ("Java Backend Developer | PrimeEnterprise Systems (2021 - Present)",
             "Designed transaction processing services in Java and Spring Boot connecting to MySQL clusters."),
            ("Software Developer | Nordic Logic (2019 - 2021)",
             "Implemented event-driven message handlers using Java and Kafka.")
        ]
    },
    {
        "filename": "10_Hannah_Abbott_Tier10_15pct.pdf",
        "name": "Hannah Abbott",
        "email": "hannah.abbott@example.com",
        "phone": "+1 (555) 020-9951",
        "title": "Frontend UI/UX Developer",
        "years": 3.0,
        "skills": ["React", "Next.js", "CSS", "HTML5", "Tailwind CSS", "JavaScript"],
        "degree": "Bachelor of Arts in Interactive Media & Web Design, Emerson College",
        "summary": "Frontend Specialist with 3 years experience crafting modern web user interfaces using React, Next.js, Tailwind CSS, and semantic HTML5.",
        "experience": [
            ("Frontend Developer | CreativePulse Interactive (2022 - Present)",
             "Designed responsive single-page applications and interactive dashboard components in React and Next.js."),
            ("UI Developer | PixelCraft Design (2021 - 2022)",
             "Created web design layouts using Tailwind CSS and modern JavaScript.")
        ]
    }
]


def generate_pdf_document(filepath: str, data: dict) -> None:
    """Generates a structured, clean PDF resume using ReportLab."""
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ResumeTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor="#1e293b",
        spaceAfter=4,
    )
    contact_style = ParagraphStyle(
        "ResumeContact",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor="#64748b",
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "ResumeHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor="#0f172a",
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor="#334155",
        spaceAfter=6,
    )
    subhead_style = ParagraphStyle(
        "ResumeSubhead",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor="#1e293b",
        spaceAfter=2,
    )

    elements = []

    # 1. Header (Name + Contact)
    elements.append(Paragraph(data["name"].upper(), title_style))
    elements.append(Paragraph(f"{data['email']} &bull; {data['phone']} &bull; {data['title']}", contact_style))
    elements.append(Spacer(1, 4))

    # 2. Professional Summary
    elements.append(Paragraph("PROFESSIONAL SUMMARY", heading_style))
    elements.append(Paragraph(data["summary"], body_style))
    elements.append(Spacer(1, 4))

    # 3. Technical Skills
    elements.append(Paragraph("TECHNICAL COMPETENCIES", heading_style))
    elements.append(Paragraph(", ".join(data["skills"]), body_style))
    elements.append(Spacer(1, 4))

    # 4. Work Experience
    elements.append(Paragraph("WORK EXPERIENCE", heading_style))
    for role_title, details in data["experience"]:
        elements.append(Paragraph(role_title, subhead_style))
        elements.append(Paragraph(f"&bull; {details}", body_style))
        elements.append(Spacer(1, 2))

    # 5. Education
    elements.append(Paragraph("EDUCATION", heading_style))
    elements.append(Paragraph(data["degree"], body_style))

    doc.build(elements)


def main():
    print("=" * 80)
    print("  GENERATE 10 GRADUATED PDF RESUMES & RUN LIVE END-TO-END MATCHING")
    print("=" * 80)

    # 1. Ensure directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\n[1/5] Generating 10 PDF resumes in: {OUTPUT_DIR}")

    pdf_files_to_upload = []

    for idx, c in enumerate(CANDIDATE_DATA, start=1):
        filepath = os.path.join(OUTPUT_DIR, c["filename"])
        generate_pdf_document(filepath, c)
        file_size_kb = os.path.getsize(filepath) / 1024.0
        print(f"      [{idx:02d}/10] Created PDF: {c['filename']} ({file_size_kb:.1f} KB)")
        with open(filepath, "rb") as f:
            pdf_bytes = f.read()
        pdf_files_to_upload.append(("files", (c["filename"], pdf_bytes, "application/pdf")))

    # 2. Create Analysis via Live API
    print(f"\n[2/5] Creating Analysis '{JOB_NAME}' on live server...")
    client = httpx.Client(timeout=45.0)

    try:
        create_resp = client.post(
            f"{BASE_URL}/analyses",
            data={"name": f"{JOB_NAME} (10 Score Tiers)", "jd_text": JOB_DESCRIPTION},
        )
        assert create_resp.status_code == 201, f"Failed: {create_resp.text}"
        analysis_id = create_resp.json()["analysis"]["id"]
        print(f"      Created Analysis ID: {analysis_id}")
    except Exception as e:
        print(f"ERROR: Cannot connect to FastAPI server at {BASE_URL}: {e}")
        return

    # 3. Confirm Requirements
    print("\n[3/5] Reviewing & Confirming Job Requirements...")
    reqs_resp = client.get(f"{BASE_URL}/analyses/{analysis_id}/requirements")
    req_skills = reqs_resp.json()["required_skills"]
    print(f"      Required Skills: {req_skills}")
    client.post(f"{BASE_URL}/analyses/{analysis_id}/requirements/confirm")
    print("      Requirements confirmed.")

    # 4. Upload 10 PDFs
    print("\n[4/5] Uploading 10 PDF resumes to analysis...")
    upload_resp = client.post(f"{BASE_URL}/analyses/{analysis_id}/resumes", files=pdf_files_to_upload)
    assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
    print(f"      Accepted: {upload_resp.json()['accepted_count']} / 10 resumes.")

    # 5. Start Analysis & Wait for Celery Worker to Rank
    print("\n[5/5] Starting Background Processing & Ranking (Celery Worker)...")
    client.post(f"{BASE_URL}/analyses/{analysis_id}/start")

    t_start = time.perf_counter()
    while time.perf_counter() - t_start < 45.0:
        status_resp = client.get(f"{BASE_URL}/analyses/{analysis_id}/status")
        status_data = status_resp.json()
        curr_state = status_data["status"]
        processed = status_data["processed"]
        total = status_data["total"]

        print(f"      [Worker Progress] Status: {curr_state} | Processed: {processed}/{total} (Elapsed: {time.perf_counter() - t_start:.1f}s)")

        if curr_state == "RANKED":
            break
        time.sleep(1.2)

    # 6. Retrieve Results Leaderboard
    cand_resp = client.get(f"{BASE_URL}/analyses/{analysis_id}/candidates")
    ranking = cand_resp.json()["ranking"]

    print("\n" + "=" * 90)
    print(f"{'RANK':<5} | {'ANONYMOUS LABEL':<16} | {'MATCH SCORE':<12} | {'REQ SKILLS':<12} | {'EXPERIENCE'}")
    print("-" * 90)
    for c in ranking:
        rank = c["rank"]
        label = c["label"]
        score = f"{c['match_score']:.1f}/100"
        req_cov = f"{c['required_skill_coverage']['value']:.1f}%" if c['required_skill_coverage']['value'] is not None else "N/A"
        exp_cov = f"{c['relevant_experience']['value']:.1f}%" if c['relevant_experience']['value'] is not None else "N/A"
        print(f"{rank:<5} | {label:<16} | {score:<12} | {req_cov:<12} | {exp_cov}")
    print("=" * 90)

    print("\n🎉 SUCCESS! 10 PDF Resumes generated and analyzed.")
    print(f"📁 PDF Files Saved To: file:///{OUTPUT_DIR.replace(os.sep, '/')}")
    print("🌐 Open Chrome at: http://localhost:5173")
    print(f"   You will see '{JOB_NAME} (10 Score Tiers)' with all 10 candidates ranked!\n")


if __name__ == "__main__":
    main()
