from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.database import get_db
from backend.models import Submission
from backend.rag_pipeline import rag_pipeline
from backend.services.grading import build_teacher_dashboard, finalize_relative_grades, get_latest_evaluation
from backend.services.ingestion import clean_text, extract_text_from_bytes, save_uploaded_file
from backend.services.master_brief import master_brief_service, serialize_master_brief
from backend.services.reporting import generate_submission_report
from backend.services.student_admin import delete_student_and_artifacts


router = APIRouter(tags=["teacher"])


@router.get("/teacher/dashboard")
def teacher_dashboard(db: Session = Depends(get_db)) -> dict:
    return build_teacher_dashboard(db)


@router.post("/finalize")
def finalize_grading(db: Session = Depends(get_db)) -> dict:
    return finalize_relative_grades(
        db,
        evaluate_callback=lambda submission, draft=False: rag_pipeline.evaluate_submission(db, submission, draft=draft),
    )


@router.post("/teacher/master-brief")
async def upload_master_brief(
    title: str | None = Form(default=None),
    text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> dict:
    file_type = "text"
    storage_path: str | None = None
    extracted_text = clean_text(text or "")

    if file is not None:
        file_bytes = await file.read()
        try:
            extracted_from_file, file_type = extract_text_from_bytes(file.filename or "master_brief.txt", file_bytes)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        extracted_text = "\n\n".join(part for part in [extracted_from_file, extracted_text] if part).strip()
        storage_path = save_uploaded_file(file.filename or "master_brief.txt", file_bytes)

    if not extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either a PDF/text file or direct text content for the master brief.",
        )

    master_brief = master_brief_service.save_master_brief(
        db,
        title=title or (file.filename.rsplit(".", 1)[0] if file and file.filename else "Course Master Brief"),
        content=extracted_text,
        file_type=file_type,
        original_filename=file.filename if file else None,
        storage_path=storage_path,
    )
    return {"master_brief": serialize_master_brief(master_brief)}


@router.delete("/teacher/student/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)) -> dict:
    return delete_student_and_artifacts(db, student_id)


@router.get("/teacher/report/{submission_id}")
def download_report(submission_id: int, db: Session = Depends(get_db)) -> FileResponse:
    submission = db.scalar(
        select(Submission)
        .options(selectinload(Submission.student), selectinload(Submission.evaluations))
        .where(Submission.id == submission_id)
    )
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    evaluation = get_latest_evaluation(submission, draft=False) or get_latest_evaluation(submission, draft=True)
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission has not been evaluated yet.")

    report_path = generate_submission_report(submission, evaluation, submission.student.grade)
    return FileResponse(path=report_path, filename=report_path.name, media_type="application/pdf")
