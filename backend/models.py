from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submissions: Mapped[list[Submission]] = relationship(
        "Submission",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="Submission.created_at.desc()",
    )
    progress_projects: Mapped[list[ProjectTrack]] = relationship(
        "ProjectTrack",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="ProjectTrack.created_at.desc()",
    )
    grade: Mapped[Grade | None] = relationship(
        "Grade",
        back_populates="student",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled Project")
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, default="text")
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    student: Mapped[Student] = relationship("Student", back_populates="submissions")
    evaluations: Mapped[list[Evaluation]] = relationship(
        "Evaluation",
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="Evaluation.created_at.desc()",
    )


class ProjectTrack(Base):
    __tablename__ = "project_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    student: Mapped[Student] = relationship("Student", back_populates="progress_projects")
    stage_submissions: Mapped[list[StageSubmission]] = relationship(
        "StageSubmission",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="StageSubmission.created_at.desc()",
    )


class StageDefinition(Base):
    __tablename__ = "stage_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    stage_submissions: Mapped[list[StageSubmission]] = relationship(
        "StageSubmission",
        back_populates="stage",
        cascade="all, delete-orphan",
        order_by="StageSubmission.created_at.desc()",
    )


class StageSubmission(Base):
    __tablename__ = "stage_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project_tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_id: Mapped[int] = mapped_column(ForeignKey("stage_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, default="text")
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    project: Mapped[ProjectTrack] = relationship("ProjectTrack", back_populates="stage_submissions")
    stage: Mapped[StageDefinition] = relationship("StageDefinition", back_populates="stage_submissions")
    evaluations: Mapped[list[StageEvaluation]] = relationship(
        "StageEvaluation",
        back_populates="stage_submission",
        cascade="all, delete-orphan",
        order_by="StageEvaluation.created_at.desc()",
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    innovation_score: Mapped[float] = mapped_column(Float, nullable=False)
    technical_score: Mapped[float] = mapped_column(Float, nullable=False)
    clarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    feedback: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    retrieved_chunks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    weak_sections: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    plagiarism_matches: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    submission: Mapped[Submission] = relationship("Submission", back_populates="evaluations")


class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    grade: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
    z_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student: Mapped[Student] = relationship("Student", back_populates="grade")


class StageEvaluation(Base):
    __tablename__ = "stage_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stage_submission_id: Mapped[int] = mapped_column(
        ForeignKey("stage_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_total_score: Mapped[float] = mapped_column(Float, nullable=False)
    scaled_score: Mapped[float] = mapped_column(Float, nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    feedback: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    context_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    retrieved_chunks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    weak_sections: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    stage_submission: Mapped[StageSubmission] = relationship("StageSubmission", back_populates="evaluations")


class LegacySubmissionStageLink(Base):
    __tablename__ = "legacy_submission_stage_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    stage_submission_id: Mapped[int] = mapped_column(
        ForeignKey("stage_submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScoringRubric(Base):
    __tablename__ = "scoring_rubrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    later_stage_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MasterBrief(Base):
    __tablename__ = "master_briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Course Master Brief")
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, default="text")
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
