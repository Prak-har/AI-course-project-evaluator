from backend.models import Evaluation, Grade, ProjectTrack, ScoringRubric, StageDefinition, StageEvaluation, StageSubmission, Student, Submission


def serialize_evaluation(evaluation: Evaluation) -> dict:
    feedback = evaluation.feedback or {}
    return {
        "id": evaluation.id,
        "innovation_score": evaluation.innovation_score,
        "technical_score": evaluation.technical_score,
        "clarity_score": evaluation.clarity_score,
        "impact_score": evaluation.impact_score,
        "total_score": evaluation.total_score,
        "feedback": feedback,
        "features": evaluation.features or {},
        "retrieved_chunks": evaluation.retrieved_chunks or [],
        "weak_sections": evaluation.weak_sections or [],
        "plagiarism_matches": evaluation.plagiarism_matches or [],
        "rubric_scores": feedback.get("rubric_scores", {}),
        "rubric_weights": feedback.get("rubric_weights", []),
        "criterion_justifications": feedback.get("criterion_justifications", {}),
        "evidence": feedback.get("evidence", {}),
        "draft": evaluation.draft,
        "created_at": evaluation.created_at,
    }


def serialize_submission(submission: Submission | None, include_content: bool = False) -> dict | None:
    if not submission:
        return None

    content = submission.content if include_content else None
    preview = submission.content[:240] + ("..." if len(submission.content) > 240 else "")
    return {
        "id": submission.id,
        "student_id": submission.student_id,
        "title": submission.title,
        "original_filename": submission.original_filename,
        "file_type": submission.file_type,
        "storage_path": submission.storage_path,
        "content": content,
        "content_preview": preview,
        "created_at": submission.created_at,
        "evaluations": [serialize_evaluation(item) for item in submission.evaluations],
    }


def serialize_grade(grade: Grade | None) -> dict | None:
    if not grade:
        return None
    return {
        "id": grade.id,
        "final_score": grade.final_score,
        "grade": grade.grade,
        "z_score": grade.z_score,
        "rank": grade.rank,
        "created_at": grade.created_at,
    }


def serialize_stage_definition(stage: StageDefinition | None) -> dict | None:
    if not stage:
        return None
    return {
        "id": stage.id,
        "name": stage.name,
        "stage_order": stage.stage_order,
        "max_marks": stage.max_marks,
        "submission_count": len(stage.stage_submissions or []),
        "created_at": stage.created_at,
    }


def serialize_stage_evaluation(evaluation: StageEvaluation | None) -> dict | None:
    if not evaluation:
        return None
    feedback = evaluation.feedback or {}
    return {
        "id": evaluation.id,
        "raw_total_score": evaluation.raw_total_score,
        "total_score": evaluation.raw_total_score,
        "scaled_score": evaluation.scaled_score,
        "max_marks": evaluation.max_marks,
        "feedback": feedback,
        "features": evaluation.features or {},
        "context_snapshot": evaluation.context_snapshot or {},
        "retrieved_chunks": evaluation.retrieved_chunks or [],
        "weak_sections": evaluation.weak_sections or [],
        "rubric_scores": feedback.get("rubric_scores", {}),
        "rubric_weights": feedback.get("rubric_weights", []),
        "criterion_justifications": feedback.get("criterion_justifications", {}),
        "evidence": feedback.get("evidence", {}),
        "created_at": evaluation.created_at,
    }


def serialize_stage_submission(stage_submission: StageSubmission | None, include_content: bool = False) -> dict | None:
    if not stage_submission:
        return None

    content = stage_submission.content if include_content else None
    preview = stage_submission.content[:240] + ("..." if len(stage_submission.content) > 240 else "")
    return {
        "id": stage_submission.id,
        "project_id": stage_submission.project_id,
        "stage_id": stage_submission.stage_id,
        "title": stage_submission.project.title if stage_submission.project else f"Stage {stage_submission.stage_id}",
        "stage": serialize_stage_definition(stage_submission.stage),
        "original_filename": stage_submission.original_filename,
        "file_type": stage_submission.file_type,
        "storage_path": stage_submission.storage_path,
        "content": content,
        "content_preview": preview,
        "created_at": stage_submission.created_at,
        "evaluations": [serialize_stage_evaluation(item) for item in stage_submission.evaluations],
    }


def _latest_stage_submissions(stage_submissions: list[StageSubmission]) -> list[StageSubmission]:
    latest_by_stage: dict[int, StageSubmission] = {}
    for submission in stage_submissions or []:
        key = submission.stage.stage_order if submission.stage else submission.stage_id
        existing = latest_by_stage.get(key)
        if not existing or submission.created_at > existing.created_at:
            latest_by_stage[key] = submission

    return [latest_by_stage[key] for key in sorted(latest_by_stage)]


def serialize_project_track(project: ProjectTrack | None, include_content: bool = False) -> dict | None:
    if not project:
        return None
    return {
        "id": project.id,
        "student_id": project.student_id,
        "title": project.title,
        "created_at": project.created_at,
        "stage_submissions": [serialize_stage_submission(item, include_content=include_content) for item in _latest_stage_submissions(project.stage_submissions)],
    }


def serialize_student(student: Student, include_submissions: bool = False, include_content: bool = False) -> dict:
    payload = {
        "id": student.id,
        "name": student.name,
        "email": student.email,
    }
    if include_submissions:
        payload["submissions"] = [serialize_submission(item, include_content=include_content) for item in student.submissions]
        payload["progress_projects"] = [serialize_project_track(item, include_content=include_content) for item in student.progress_projects]
    return payload


def serialize_scoring_rubric(rubric: ScoringRubric | None) -> dict | None:
    if not rubric:
        return None
    return {
        "id": rubric.id,
        "key": rubric.key,
        "name": rubric.name,
        "weight": rubric.weight,
        "display_order": rubric.display_order,
        "later_stage_only": rubric.later_stage_only,
        "created_at": rubric.created_at,
    }
