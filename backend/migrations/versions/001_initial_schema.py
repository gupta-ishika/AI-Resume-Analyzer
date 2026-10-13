"""Initial relational schema for analyses, requirements,
resumes, candidates, matching, and explanations.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-10-13 10:35:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")

    # 1. analyses
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "scoring_config_version", sa.String(length=20), nullable=False, server_default="1.0.0"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analyses_updated_at", "analyses", ["updated_at"])
    op.create_index("ix_analyses_deletion", "analyses", ["deletion_requested_at"])

    # 2. job_requirements
    op.create_table(
        "job_requirements",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.String(length=36),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("required_skills", json_type, nullable=False),
        sa.Column("preferred_skills", json_type, nullable=False),
        sa.Column("experience_requirements", json_type, nullable=False),
        sa.Column("education_requirements", json_type, nullable=False),
        sa.Column("explicit_requirements", json_type, nullable=False),
        sa.Column("job_relevant_text", sa.Text(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. resumes
    op.create_table(
        "resumes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.String(length=36),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("failure_category", sa.String(length=50), nullable=True),
        sa.Column("failure_reason_code", sa.String(length=50), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column(
            "canonical_resume_id",
            sa.String(length=36),
            sa.ForeignKey("resumes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("temp_storage_key", sa.String(length=255), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resumes_analysis_status", "resumes", ["analysis_id", "status"])
    op.create_index("ix_resumes_content_hash", "resumes", ["analysis_id", "content_hash"])

    # 4. candidates
    op.create_table(
        "candidates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.String(length=36),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "resume_id",
            sa.String(length=36),
            sa.ForeignKey("resumes.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("display_label", sa.String(length=50), nullable=True),
        sa.Column("candidate_name", sa.String(length=255), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("contact_other", json_type, nullable=False),
        sa.Column("extracted_skills", json_type, nullable=False),
        sa.Column("extracted_experience", json_type, nullable=False),
        sa.Column("extracted_projects", json_type, nullable=False),
        sa.Column("extracted_education", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("analysis_id", "display_label", name="uq_candidates_analysis_label"),
    )
    op.create_index("ix_candidates_analysis", "candidates", ["analysis_id"])

    # 5. match_results
    op.create_table(
        "match_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.String(length=36),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "analysis_id",
            sa.String(length=36),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("component_scores", json_type, nullable=False),
        sa.Column("matching_evidence", json_type, nullable=False),
        sa.Column(
            "scoring_config_version", sa.String(length=20), nullable=False, server_default="1.0.0"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("analysis_id", "rank", name="uq_match_results_analysis_rank"),
    )
    op.create_index("ix_match_results_analysis_rank", "match_results", ["analysis_id", "rank"])

    # 6. explanations
    op.create_table(
        "explanations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.String(length=36),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "analysis_id",
            sa.String(length=36),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=50), nullable=False),
        sa.Column("explanation_content", json_type, nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("generation_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_explanations_state", "explanations", ["state"])


def downgrade() -> None:
    op.drop_table("explanations")
    op.drop_table("match_results")
    op.drop_table("candidates")
    op.drop_table("resumes")
    op.drop_table("job_requirements")
    op.drop_table("analyses")
