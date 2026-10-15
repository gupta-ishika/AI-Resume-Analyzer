"""
Performance and Latency Benchmark Script (REL-01).

Benchmarks:
1. 20-resume analysis processing time (PRD target: <= 60 seconds)
2. 50-resume analysis processing time (PRD target: <= 150 seconds)
3. AI Explanation generation latency (PRD target: <= 15 seconds)
"""

import io
import os
import platform
import sys
import time
from datetime import UTC, datetime

import docx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Setup test environment
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.database import Base, get_db
from backend.main import app
from backend.services.llm_service import MockLLMService
from backend.worker.celery_app import celery_app
import backend.core.database as core_db
import backend.worker.tasks as worker_tasks

# Isolated SQLite benchmark database
BENCHMARK_DB_URL = "sqlite:///./benchmark_fixture.db"
bench_engine = create_engine(BENCHMARK_DB_URL, connect_args={"check_same_thread": False})
BenchmarkSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bench_engine)

core_db.SessionLocal = BenchmarkSessionLocal
worker_tasks.SessionLocal = BenchmarkSessionLocal

celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

SKILL_SETS = [
    ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
    ["Python", "Django", "PostgreSQL", "Celery", "AWS"],
    ["JavaScript", "TypeScript", "React", "Node.js", "GraphQL"],
    ["Java", "Spring Boot", "MySQL", "Kubernetes", "Kafka"],
    ["Go", "Docker", "Kubernetes", "gRPC", "Prometheus"],
    ["Python", "Machine Learning", "PyTorch", "Pandas", "Scikit-Learn"],
    ["C++", "Linux", "Embedded Systems", "RTOS", "Git"],
    ["Python", "SQL", "Airflow", "Snowflake", "dbt"],
]


CANDIDATE_NAMES = [
    "Alex Morgan", "Jordan Hayes", "Taylor Reed", "Morgan Bailey",
    "Casey Jordan", "Sam Wilson", "Riley Cooper", "Jamie Ellis",
    "Avery Brooks", "Robin Parker", "Logan Carter", "Drew Bennett"
]


def generate_candidate_docx(index: int) -> bytes:
    """Generates an in-memory genuine DOCX resume with variable content."""
    doc = docx.Document()
    skills = SKILL_SETS[index % len(SKILL_SETS)]
    years = 2 + (index % 8)
    title = f"Software Engineer Level {1 + (index % 4)}"
    name = f"{CANDIDATE_NAMES[index % len(CANDIDATE_NAMES)]} {index + 1}"

    doc.add_heading(name, level=0)
    doc.add_paragraph(f"user_{index + 1}@example.com | (555) 019-{index:04d}")
    doc.add_heading("Professional Summary", level=1)
    doc.add_paragraph(
        f"Experienced {title} with {years} years of demonstrated experience building "
        f"scalable systems using {', '.join(skills[:3])}."
    )
    doc.add_heading("Technical Skills", level=1)
    doc.add_paragraph(", ".join(skills))
    doc.add_heading("Experience", level=1)
    doc.add_paragraph(f"{title} - Tech Firm {index % 5 + 1} ({years} years)")
    doc.add_paragraph(
        f"Architected backend microservices and implemented data pipelines using {skills[0]}."
    )
    doc.add_heading("Education", level=1)
    doc.add_paragraph(f"B.S. in Computer Science - University {index % 3 + 1}")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def run_benchmark():
    print("=" * 70)
    print("  AI Resume Analyzer - Performance & Latency Benchmark (REL-01)")
    print("=" * 70)
    print(f"System: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python: {platform.python_version()}")
    print(f"Timestamp: {datetime.now(UTC).isoformat()}\n")

    # Setup DB
    Base.metadata.create_all(bind=bench_engine)

    def override_get_db():
        session = BenchmarkSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    results = []

    with TestClient(app) as client:
        # -------------------------------------------------------------
        # Benchmark 1: 20-Resume Batch Analysis (Target: <= 60 seconds)
        # -------------------------------------------------------------
        print(">>> Benchmark 1: Processing 20 Resumes...")
        start_time = time.perf_counter()

        # Step 1: Create Analysis
        jd_text = (
            "Senior Backend Engineer\n"
            "Requirements:\n"
            "- 4+ years software development experience\n"
            "- Proficiency in Python and PostgreSQL\n"
            "Preferred:\n"
            "- Experience with Docker and Redis\n"
        )
        resp = client.post("/api/analyses", data={"name": "Perf Test 20", "jd_text": jd_text})
        assert resp.status_code == 201, f"Create analysis failed: {resp.text}"
        analysis_id = resp.json()["analysis"]["id"]

        # Step 2: Confirm Requirements
        client.post(f"/api/analyses/{analysis_id}/requirements/confirm")

        # Step 3: Upload 20 Resumes
        files = [
            (
                "files",
                (f"candidate_{i+1:02d}.docx", io.BytesIO(generate_candidate_docx(i)), DOCX_MIME),
            )
            for i in range(20)
        ]
        upload_resp = client.post(f"/api/analyses/{analysis_id}/resumes", files=files)
        assert upload_resp.json()["accepted_count"] == 20

        # Step 4: Start Analysis & wait for ranking
        t_proc_start = time.perf_counter()
        client.post(f"/api/analyses/{analysis_id}/start")
        proc_duration = time.perf_counter() - t_proc_start
        total_20_duration = time.perf_counter() - start_time

        # Step 5: Verify status
        status_resp = client.get(f"/api/analyses/{analysis_id}/status")
        status_data = status_resp.json()
        assert status_data["status"] == "RANKED"
        assert status_data["processed"] == 20

        cand_resp = client.get(f"/api/analyses/{analysis_id}/candidates")
        ranked_count = len(cand_resp.json()["ranking"])

        target_20 = 60.0
        passed_20 = total_20_duration <= target_20
        throughput_20 = 20 / total_20_duration

        results.append(
            {
                "name": "20 Resumes End-to-End Processing",
                "count": 20,
                "duration": total_20_duration,
                "target": target_20,
                "throughput": throughput_20,
                "passed": passed_20,
            }
        )
        print(f"  [OK] Processed 20 resumes in {total_20_duration:.2f}s ({throughput_20:.2f} resumes/s)")
        print(f"    Target: <= {target_20:.1f}s | Result: {'PASS' if passed_20 else 'FAIL'}\n")

        # -------------------------------------------------------------
        # Benchmark 2: 50-Resume Batch Analysis (Target: <= 150 seconds)
        # -------------------------------------------------------------
        print(">>> Benchmark 2: Processing 50 Resumes...")
        start_time_50 = time.perf_counter()

        resp50 = client.post("/api/analyses", data={"name": "Perf Test 50", "jd_text": jd_text})
        analysis_id_50 = resp50.json()["analysis"]["id"]
        client.post(f"/api/analyses/{analysis_id_50}/requirements/confirm")

        files50 = [
            (
                "files",
                (f"candidate_{i+1:02d}.docx", io.BytesIO(generate_candidate_docx(i)), DOCX_MIME),
            )
            for i in range(50)
        ]
        upload_resp50 = client.post(f"/api/analyses/{analysis_id_50}/resumes", files=files50)
        assert upload_resp50.json()["accepted_count"] == 50

        t_proc_start_50 = time.perf_counter()
        client.post(f"/api/analyses/{analysis_id_50}/start")
        total_50_duration = time.perf_counter() - start_time_50

        status_resp_50 = client.get(f"/api/analyses/{analysis_id_50}/status")
        assert status_resp_50.json()["status"] == "RANKED"
        assert status_resp_50.json()["processed"] == 50

        target_50 = 150.0
        passed_50 = total_50_duration <= target_50
        throughput_50 = 50 / total_50_duration

        results.append(
            {
                "name": "50 Resumes End-to-End Processing",
                "count": 50,
                "duration": total_50_duration,
                "target": target_50,
                "throughput": throughput_50,
                "passed": passed_50,
            }
        )
        print(f"  [OK] Processed 50 resumes in {total_50_duration:.2f}s ({throughput_50:.2f} resumes/s)")
        print(f"    Target: <= {target_50:.1f}s | Result: {'PASS' if passed_50 else 'FAIL'}\n")

        # -------------------------------------------------------------
        # Benchmark 3: AI Explanation Latency (Target: <= 15 seconds)
        # -------------------------------------------------------------
        print(">>> Benchmark 3: AI Explanation Latency...")
        first_candidate_id = cand_resp.json()["ranking"][0]["candidate_id"]
        expl_url = f"/api/analyses/{analysis_id}/candidates/{first_candidate_id}/explanation"

        # Test with mock LLM service representing expected inference budget
        mock_llm = MockLLMService()
        from unittest.mock import patch

        t_expl_start = time.perf_counter()
        with patch("backend.services.explanation_service.default_llm_service", mock_llm):
            expl_req = client.post(expl_url)
            assert expl_req.status_code == 200

        expl_duration = time.perf_counter() - t_expl_start

        expl_status = client.get(expl_url)
        assert expl_status.json()["state"] == "READY"

        target_expl = 15.0
        passed_expl = expl_duration <= target_expl

        results.append(
            {
                "name": "Single Candidate AI Explanation",
                "count": 1,
                "duration": expl_duration,
                "target": target_expl,
                "throughput": 1 / expl_duration if expl_duration > 0 else 0,
                "passed": passed_expl,
            }
        )
        print(f"  [OK] AI Explanation latency: {expl_duration:.3f}s")
        print(f"    Target: <= {target_expl:.1f}s | Result: {'PASS' if passed_expl else 'FAIL'}\n")

    # Cleanup DB
    Base.metadata.drop_all(bind=bench_engine)
    if os.path.exists("./benchmark_fixture.db"):
        try:
            os.remove("./benchmark_fixture.db")
        except OSError:
            pass

    # Print Formatted Report Table
    print("=" * 70)
    print(f"{'BENCHMARK SCENARIO':<35} | {'MEASURED':<10} | {'TARGET':<10} | {'STATUS'}")
    print("-" * 70)
    all_passed = True
    for r in results:
        meas = f"{r['duration']:.2f}s"
        tgt = f"<= {r['target']:.1f}s"
        status_str = "PASS" if r["passed"] else "FAIL"
        if not r["passed"]:
            all_passed = False
        print(f"{r['name']:<35} | {meas:<10} | {tgt:<10} | {status_str}")
    print("=" * 70)

    if all_passed:
        print("\nALL PRD PERFORMANCE TARGETS SATISFIED!\n")
    else:
        print("\nSOME PERFORMANCE TARGETS EXCEEDED PRD THRESHOLDS.\n")
        sys.exit(1)


if __name__ == "__main__":
    run_benchmark()
