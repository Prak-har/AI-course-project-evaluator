from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.database import get_db
from backend.models import ProjectTrack, StageSubmission, Student, Submission
from backend.services.continuous_evaluation import continuous_evaluation_service
from backend.services.grading import (
    build_final_marks_payload,
    build_marks_comparison,
    build_stage_score_snapshot,
    get_latest_evaluation,
    get_latest_project_track,
    get_latest_submission,
    get_total_stage_marks,
)
from backend.services.serializers import serialize_student, serialize_stage_definition


router = APIRouter(tags=["students"])


@router.get("/student/{student_id}")
def get_student_dashboard(student_id: int, db: Session = Depends(get_db)) -> dict:
    stage_definitions = continuous_evaluation_service.list_stages(db)
    total_stage_marks = get_total_stage_marks(stage_definitions)

    student = db.scalar(
        select(Student)
        .options(
            selectinload(Student.submissions).selectinload(Submission.evaluations),
            selectinload(Student.progress_projects)
            .selectinload(ProjectTrack.stage_submissions)
            .selectinload(StageSubmission.stage),
            selectinload(Student.progress_projects)
            .selectinload(ProjectTrack.stage_submissions)
            .selectinload(StageSubmission.evaluations),
            selectinload(Student.grade),
        )
        .where(Student.id == student_id)
    )
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    cohort_students = list(
        db.scalars(
            select(Student)
            .options(
                selectinload(Student.submissions).selectinload(Submission.evaluations),
                selectinload(Student.progress_projects)
                .selectinload(ProjectTrack.stage_submissions)
                .selectinload(StageSubmission.stage),
                selectinload(Student.progress_projects)
                .selectinload(ProjectTrack.stage_submissions)
                .selectinload(StageSubmission.evaluations),
                selectinload(Student.grade),
            )
        )
    )

    score_pool: list[float] = []
    for cohort_student in cohort_students:
        latest_project = get_latest_project_track(cohort_student)
        stage_snapshot = build_stage_score_snapshot(latest_project, total_stage_marks=total_stage_marks) if latest_project else None
        latest_submission = get_latest_submission(cohort_student)
        latest_draft = get_latest_evaluation(latest_submission, draft=True)
        latest_final = get_latest_evaluation(latest_submission, draft=False)

        if stage_snapshot and stage_snapshot["evaluated_stage_count"]:
            score_pool.append(stage_snapshot["marks_earned"])
        elif latest_final:
            score_pool.append(latest_final.total_score)
        elif latest_draft:
            score_pool.append(latest_draft.total_score)
        elif cohort_student.grade:
            score_pool.append(cohort_student.grade.final_score)

    latest_project = get_latest_project_track(student)
    latest_submission = get_latest_submission(student)
    latest_draft = get_latest_evaluation(latest_submission, draft=True)
    latest_final = get_latest_evaluation(latest_submission, draft=False)
    stage_snapshot = build_stage_score_snapshot(latest_project, total_stage_marks=total_stage_marks) if latest_project else None
    current_marks = None
    marks_possible = total_stage_marks or None
    if stage_snapshot and stage_snapshot["evaluated_stage_count"]:
        current_marks = stage_snapshot["marks_earned"]
        marks_possible = stage_snapshot["marks_possible"]
    elif latest_final:
        current_marks = latest_final.total_score
        marks_possible = 10.0
    elif latest_draft:
        current_marks = latest_draft.total_score
        marks_possible = 10.0
    elif student.grade:
        current_marks = student.grade.final_score
        marks_possible = total_stage_marks or 10.0

    return {
        "student": serialize_student(student, include_submissions=True, include_content=True),
        "stage_definitions": [serialize_stage_definition(item) for item in stage_definitions],
        "final_marks": build_final_marks_payload(
            current_marks,
            marks_possible,
            rank=student.grade.rank if student.grade else None,
            z_score=student.grade.z_score if student.grade else None,
            finalized_at=student.grade.created_at if student.grade else None,
        ),
        "stage_breakdown": stage_snapshot["stage_breakdown"] if stage_snapshot else [],
        "comparison": build_marks_comparison(
            current_marks,
            score_pool=score_pool,
            rank=student.grade.rank if student.grade else None,
            z_score=student.grade.z_score if student.grade else None,
            total_possible_marks=marks_possible,
        ),
    }
