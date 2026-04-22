from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Submission, Student
from backend.rag_pipeline import rag_pipeline
from backend.schemas import EvaluateRequest, UploadResponse
from backend.services.ingestion import clean_text, extract_text_from_bytes, save_uploaded_file
from backend.services.serializers import serialize_evaluation


router = APIRouter(tags=["submissions"])


@router.post("/upload", response_model=UploadResponse)
async def upload_project(
    student_id: int = Form(...),
    title: str | None = Form(default=None),
    text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> UploadResponse:
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    file_type = "text"
    storage_path: str | None = None
    extracted_text = clean_text(text or "")

    if file is not None:
        file_bytes = await file.read()
        try:
            extracted_from_file, file_type = extract_text_from_bytes(file.filename or "submission.txt", file_bytes)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        extracted_text = "\n\n".join(part for part in [extracted_from_file, extracted_text] if part).strip()
        storage_path = save_uploaded_file(file.filename or "submission.txt", file_bytes)

    if not extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either a PDF/text file or direct text content.",
        )

    submission = Submission(
        student_id=student_id,
        title=title or ((file.filename or "Project Submission").rsplit(".", 1)[0] if file else "Project Submission"),
        original_filename=file.filename if file else None,
        file_type=file_type,
        storage_path=storage_path,
        content=extracted_text,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    ingestion_result = rag_pipeline.ingest_submission(submission)
    return UploadResponse(
        submission_id=submission.id,
        title=submission.title,
        file_type=submission.file_type,
        embedded=ingestion_result["embedded"],
        warning=ingestion_result.get("warning"),
        created_at=submission.created_at,
    )


@router.post("/evaluate")
def evaluate_project(payload: EvaluateRequest, db: Session = Depends(get_db)) -> dict:
    submission = db.get(Submission, payload.submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    evaluation = rag_pipeline.evaluate_submission(db, submission, draft=payload.draft)
    return {"evaluation": serialize_evaluation(evaluation)}
