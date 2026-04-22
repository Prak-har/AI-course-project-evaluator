from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import (
    RubricCreateRequest,
    RubricUpdateRequest,
    StageCreateRequest,
    StageEvaluateRequest,
    StageUpdateRequest,
    StageUploadResponse,
)
from backend.services.continuous_evaluation import continuous_evaluation_service
from backend.services.grading import build_final_marks_payload, build_stage_score_snapshot, get_total_stage_marks
from backend.services.ingestion import clean_text, extract_text_from_bytes, save_uploaded_file
from backend.services.rubrics import rubric_service
from backend.services.serializers import (
    serialize_scoring_rubric,
    serialize_stage_definition,
    serialize_stage_evaluation,
    serialize_stage_submission,
    serialize_student,
)


router = APIRouter(tags=["continuous"])


@router.post("/continuous/upload", response_model=StageUploadResponse)
async def upload_stage_progress(
    student_id: int = Form(...),
    project_title: str = Form(...),
    stage_id: int = Form(...),
    text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> StageUploadResponse:
    continuous_evaluation_service.validate_stage_submission(
        db,
        student_id=student_id,
        project_title=project_title,
        stage_id=stage_id,
    )

    file_type = "text"
    storage_path: str | None = None
    extracted_text = clean_text(text or "")

    if file is not None:
        file_bytes = await file.read()
        try:
            extracted_from_file, file_type = extract_text_from_bytes(file.filename or "stage_submission.txt", file_bytes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        extracted_text = "\n\n".join(part for part in [extracted_from_file, extracted_text] if part).strip()
        storage_path = save_uploaded_file(file.filename or "stage_submission.txt", file_bytes)

    if not extracted_text:
        raise HTTPException(status_code=400, detail="Provide either a PDF/text file or direct text content.")

    try:
        submission = continuous_evaluation_service.save_stage_submission(
            db,
            student_id=student_id,
            project_title=project_title,
            stage_id=stage_id,
            content=extracted_text,
            file_type=file_type,
            original_filename=file.filename if file else None,
            storage_path=storage_path,
        )
    except Exception:
        if storage_path:
            path = Path(storage_path)
            if path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass
        raise

    warning: str | None = None
    embedded = False
    try:
        continuous_evaluation_service.evaluate_stage_submission(db, submission.id)
        embedded = True
    except HTTPException as exc:
        if exc.status_code >= 500:
            warning = str(exc.detail)
        else:
            raise

    return StageUploadResponse(
        stage_submission_id=submission.id,
        project_id=submission.project_id,
        stage_id=submission.stage_id,
        embedded=embedded,
        warning=warning,
        created_at=submission.created_at,
    )


@router.post("/continuous/evaluate")
def evaluate_stage_progress(payload: StageEvaluateRequest, db: Session = Depends(get_db)) -> dict:
    evaluation = continuous_evaluation_service.evaluate_stage_submission(db, payload.stage_submission_id)
    return {"evaluation": serialize_stage_evaluation(evaluation)}


@router.get("/continuous/stage-submission/{stage_submission_id}")
def get_stage_feedback(stage_submission_id: int, db: Session = Depends(get_db)) -> dict:
    submission = continuous_evaluation_service.get_stage_submission(db, stage_submission_id)
    latest_evaluation = submission.evaluations[0] if submission.evaluations else None
    stage_definitions = continuous_evaluation_service.list_stages(db)
    total_stage_marks = get_total_stage_marks(stage_definitions)
    stage_snapshot = build_stage_score_snapshot(submission.project, total_stage_marks=total_stage_marks)

    return {
        "student": serialize_student(submission.project.student),
        "project": {
            "id": submission.project.id,
            "title": submission.project.title,
        },
        "stage_submission": serialize_stage_submission(submission, include_content=True),
        "latest_evaluation": serialize_stage_evaluation(latest_evaluation),
        "stage_definitions": [serialize_stage_definition(item) for item in stage_definitions],
        "stage_breakdown": stage_snapshot["stage_breakdown"] if stage_snapshot else [],
        "final_marks": build_final_marks_payload(
            stage_snapshot["marks_earned"] if stage_snapshot else submission.project.student.grade.final_score if submission.project.student.grade else None,
            total_stage_marks or None,
            rank=submission.project.student.grade.rank if submission.project.student.grade else None,
            z_score=submission.project.student.grade.z_score if submission.project.student.grade else None,
            finalized_at=submission.project.student.grade.created_at if submission.project.student.grade else None,
        ),
    }


@router.delete("/continuous/stage-submission/{stage_submission_id}")
def delete_stage_progress(stage_submission_id: int, student_id: int, db: Session = Depends(get_db)) -> dict:
    return continuous_evaluation_service.delete_stage_submission(db, stage_submission_id, student_id)


@router.put("/teacher/stages/{stage_id}")
def update_stage(stage_id: int, payload: StageUpdateRequest, db: Session = Depends(get_db)) -> dict:
    stage = continuous_evaluation_service.update_stage(db, stage_id, payload.name, payload.max_marks)
    return {"stage": serialize_stage_definition(stage)}


@router.post("/teacher/stages")
def create_stage(payload: StageCreateRequest, db: Session = Depends(get_db)) -> dict:
    stage = continuous_evaluation_service.create_stage(db, payload.name, payload.max_marks)
    return {"stage": serialize_stage_definition(stage)}


@router.delete("/teacher/stages/{stage_id}")
def delete_stage(stage_id: int, db: Session = Depends(get_db)) -> dict:
    return continuous_evaluation_service.delete_stage(db, stage_id)


@router.post("/teacher/rubrics")
def create_rubric(payload: RubricCreateRequest, db: Session = Depends(get_db)) -> dict:
    rubric = rubric_service.create_rubric(
        db,
        name=payload.name,
        weight=payload.weight,
        later_stage_only=payload.later_stage_only,
    )
    return {"rubric": serialize_scoring_rubric(rubric)}


@router.put("/teacher/rubrics/{rubric_id}")
def update_rubric(rubric_id: int, payload: RubricUpdateRequest, db: Session = Depends(get_db)) -> dict:
    rubric = rubric_service.update_rubric(
        db,
        rubric_id,
        name=payload.name,
        weight=payload.weight,
        later_stage_only=payload.later_stage_only,
    )
    return {"rubric": serialize_scoring_rubric(rubric)}


@router.delete("/teacher/rubrics/{rubric_id}")
def delete_rubric(rubric_id: int, db: Session = Depends(get_db)) -> dict:
    return rubric_service.delete_rubric(db, rubric_id)
