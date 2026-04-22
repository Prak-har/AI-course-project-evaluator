import shutil
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.config import get_settings
from backend.models import ProjectTrack, StageSubmission, Student, Submission
from backend.services.vector_store import submission_vector_store


settings = get_settings()


def _safe_unlink(path: Path | None) -> None:
    if not path or not path.exists():
        return
    try:
        path.unlink()
    except OSError:
        return


def _safe_rmtree(path: Path) -> None:
    if not path.exists():
        return
    try:
        shutil.rmtree(path, ignore_errors=True)
    except OSError:
        return


def delete_student_and_artifacts(db: Session, student_id: int) -> dict:
    student = db.scalar(
        select(Student)
        .options(
            selectinload(Student.submissions).selectinload(Submission.evaluations),
            selectinload(Student.progress_projects)
            .selectinload(ProjectTrack.stage_submissions)
            .selectinload(StageSubmission.evaluations),
            selectinload(Student.grade),
        )
        .where(Student.id == student_id)
    )
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    submission_refs = [
        {
            "submission_id": submission.id,
            "storage_path": Path(submission.storage_path) if submission.storage_path else None,
            "report_path": settings.reports_dir / f"submission_{submission.id}_report.pdf",
            "faiss_path": submission_vector_store.base_dir / str(submission.id),
        }
        for submission in student.submissions
    ]
    stage_submission_refs = [
        {"storage_path": Path(submission.storage_path) if submission.storage_path else None}
        for project in student.progress_projects
        for submission in project.stage_submissions
    ]

    student_name = student.name
    submission_count = len(student.submissions)
    db.delete(student)
    db.commit()

    for reference in submission_refs:
        _safe_unlink(reference["storage_path"])
        _safe_unlink(reference["report_path"])
        _safe_rmtree(reference["faiss_path"])
    for reference in stage_submission_refs:
        _safe_unlink(reference["storage_path"])

    return {
        "deleted_student_id": student_id,
        "deleted_student_name": student_name,
        "deleted_submissions": submission_count,
        "message": f"Deleted {student_name} and cleaned up related records.",
    }
