from statistics import mean, pstdev

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.models import Evaluation, Grade, ProjectTrack, StageSubmission, Student, Submission
from backend.services.continuous_evaluation import continuous_evaluation_service
from backend.services.master_brief import master_brief_service, serialize_master_brief
from backend.services.rubrics import rubric_service
from backend.services.serializers import (
    serialize_evaluation,
    serialize_scoring_rubric,
    serialize_stage_definition,
    serialize_stage_evaluation,
    serialize_stage_submission,
    serialize_student,
    serialize_submission,
)


def get_latest_submission(student: Student) -> Submission | None:
    if not student.submissions:
        return None
    return max(student.submissions, key=lambda item: item.created_at)


def get_latest_evaluation(submission: Submission | None, draft: bool | None = None) -> Evaluation | None:
    if not submission:
        return None

    evaluations = submission.evaluations
    filtered = evaluations if draft is None else [item for item in evaluations if item.draft is draft]
    if not filtered:
        return None
    return max(filtered, key=lambda item: item.created_at)


def get_latest_project_track(student: Student) -> ProjectTrack | None:
    if not student.progress_projects:
        return None
    return max(student.progress_projects, key=lambda item: item.created_at)


def get_latest_stage_submission(project: ProjectTrack | None) -> StageSubmission | None:
    if not project or not project.stage_submissions:
        return None
    return max(
        project.stage_submissions,
        key=lambda item: ((item.stage.stage_order if item.stage else 0), item.created_at),
    )


def get_latest_stage_evaluation(stage_submission: StageSubmission | None):
    if not stage_submission or not stage_submission.evaluations:
        return None
    return max(stage_submission.evaluations, key=lambda item: item.created_at)


def get_total_stage_marks(stage_definitions: list) -> float:
    return round(sum(float(item.max_marks or 0.0) for item in stage_definitions), 2)


def get_latest_stage_submissions_by_order(project: ProjectTrack | None) -> dict[int, StageSubmission]:
    if not project:
        return {}

    latest_by_stage: dict[int, StageSubmission] = {}
    for submission in project.stage_submissions:
        order = submission.stage.stage_order if submission.stage else 0
        existing = latest_by_stage.get(order)
        if not existing or submission.created_at > existing.created_at:
            latest_by_stage[order] = submission
    return latest_by_stage


def build_stage_score_snapshot(project: ProjectTrack | None, total_stage_marks: float | None = None) -> dict | None:
    latest_by_stage = get_latest_stage_submissions_by_order(project)
    if not latest_by_stage:
        return None

    total_marks = 0.0
    latest_submission = None
    latest_evaluation = None
    evaluated_stage_count = 0
    stage_breakdown: list[dict] = []

    for order in sorted(latest_by_stage):
        submission = latest_by_stage[order]
        evaluation = get_latest_stage_evaluation(submission)
        latest_submission = submission
        if evaluation:
            latest_evaluation = evaluation
            total_marks += evaluation.scaled_score
            evaluated_stage_count += 1

        stage_breakdown.append(
            {
                "stage_id": submission.stage_id,
                "stage_name": submission.stage.name if submission.stage else f"Stage {order}",
                "stage_order": order,
                "max_marks": submission.stage.max_marks if submission.stage else None,
                "scaled_score": evaluation.scaled_score if evaluation else None,
                "raw_total_score": evaluation.raw_total_score if evaluation else None,
                "submission_id": submission.id,
            }
        )

    marks_possible = round(
        total_stage_marks if total_stage_marks is not None else sum(item["max_marks"] or 0.0 for item in stage_breakdown),
        2,
    )

    return {
        "project": project,
        "submission": latest_submission,
        "evaluation": latest_evaluation,
        "marks_earned": round(total_marks, 2),
        "marks_possible": marks_possible,
        "evaluated_stage_count": evaluated_stage_count,
        "submitted_stage_count": len(latest_by_stage),
        "stage_breakdown": stage_breakdown,
    }


def build_marks_comparison(
    current_score: float | None,
    *,
    score_pool: list[float],
    rank: int | None = None,
    z_score: float | None = None,
    total_possible_marks: float | None = None,
) -> dict | None:
    if current_score is None:
        return None

    normalized_pool = [round(float(score), 2) for score in score_pool if score is not None]
    class_average = round(mean(normalized_pool), 2) if normalized_pool else None
    top_score = round(max(normalized_pool), 2) if normalized_pool else None

    return {
        "current_marks": round(current_score, 2),
        "total_possible_marks": round(total_possible_marks, 2) if total_possible_marks is not None else None,
        "class_average": class_average,
        "top_score": top_score,
        "difference_from_average": round(current_score - class_average, 2) if class_average is not None else None,
        "gap_to_top": round(top_score - current_score, 2) if top_score is not None else None,
        "rank": rank,
        "ranked_count": len(normalized_pool),
        "z_score": round(z_score, 4) if z_score is not None else None,
    }


def build_final_marks_payload(
    earned: float | None,
    possible: float | None,
    *,
    rank: int | None = None,
    z_score: float | None = None,
    finalized_at=None,
) -> dict | None:
    if earned is None and rank is None and z_score is None:
        return None

    return {
        "earned": round(float(earned), 2) if earned is not None else None,
        "possible": round(float(possible), 2) if possible is not None else None,
        "rank": rank,
        "z_score": round(float(z_score), 4) if z_score is not None else None,
        "finalized_at": finalized_at,
    }


def build_teacher_dashboard(db: Session) -> dict:
    stage_definitions = continuous_evaluation_service.list_stages(db)
    rubrics = rubric_service.list_rubrics(db)
    total_stage_marks = get_total_stage_marks(stage_definitions)

    students = list(
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
            .order_by(Student.name)
        )
    )

    rows: list[dict] = []
    ranking: list[dict] = []
    score_pool: list[float] = []
    row_meta: list[tuple[dict, float | None, float | None, Student]] = []
    ranking_meta: list[tuple[dict, float, float | None]] = []

    for student in students:
        latest_submission = get_latest_submission(student)
        latest_draft = get_latest_evaluation(latest_submission, draft=True)
        latest_final = get_latest_evaluation(latest_submission, draft=False)
        latest_project = get_latest_project_track(student)
        latest_stage_submission = get_latest_stage_submission(latest_project)
        latest_stage_evaluation = get_latest_stage_evaluation(latest_stage_submission)
        stage_snapshot = build_stage_score_snapshot(latest_project, total_stage_marks=total_stage_marks) if latest_project else None

        score_for_stats = None
        marks_possible = None
        if stage_snapshot and stage_snapshot["evaluated_stage_count"]:
            score_for_stats = stage_snapshot["marks_earned"]
            marks_possible = stage_snapshot["marks_possible"]
        elif latest_final:
            score_for_stats = latest_final.total_score
            marks_possible = 10.0
        elif latest_draft:
            score_for_stats = latest_draft.total_score
            marks_possible = 10.0
        elif student.grade:
            score_for_stats = student.grade.final_score
            marks_possible = total_stage_marks or None

        if score_for_stats is not None:
            score_pool.append(score_for_stats)

        visible_final_marks = stage_snapshot["marks_earned"] if stage_snapshot and stage_snapshot["evaluated_stage_count"] else score_for_stats
        row_payload = {
            "student": serialize_student(student),
            "latest_submission": serialize_submission(latest_submission),
            "latest_draft": serialize_evaluation(latest_draft) if latest_draft else None,
            "latest_final": serialize_evaluation(latest_final) if latest_final else None,
            "latest_stage_submission": serialize_stage_submission(latest_stage_submission),
            "latest_stage_evaluation": serialize_stage_evaluation(latest_stage_evaluation),
            "final_marks": build_final_marks_payload(
                visible_final_marks,
                marks_possible or total_stage_marks or None,
                rank=student.grade.rank if student.grade else None,
                z_score=student.grade.z_score if student.grade else None,
                finalized_at=student.grade.created_at if student.grade else None,
            ),
            "stage_breakdown": stage_snapshot["stage_breakdown"] if stage_snapshot else [],
        }
        rows.append(row_payload)
        row_meta.append((row_payload, visible_final_marks, marks_possible or total_stage_marks or None, student))

        if student.grade and (latest_stage_submission or latest_submission):
            ranking_payload = {
                "student": serialize_student(student),
                "submission": serialize_stage_submission(latest_stage_submission) if latest_stage_submission else serialize_submission(latest_submission),
                "final_marks": build_final_marks_payload(
                    student.grade.final_score,
                    marks_possible or total_stage_marks or None,
                    rank=student.grade.rank,
                    z_score=student.grade.z_score,
                    finalized_at=student.grade.created_at,
                ),
                "stage_breakdown": stage_snapshot["stage_breakdown"] if stage_snapshot else [],
            }
            ranking.append(ranking_payload)
            ranking_meta.append((ranking_payload, student.grade.final_score, marks_possible or total_stage_marks or None))

    average = round(mean(score_pool), 2) if score_pool else 0.0
    std_dev = round(pstdev(score_pool), 2) if len(score_pool) > 1 else 0.0
    top_score = round(max(score_pool), 2) if score_pool else 0.0

    for row_payload, current_score, marks_possible, student in row_meta:
        grade = student.grade
        row_payload["comparison"] = build_marks_comparison(
            current_score,
            score_pool=score_pool,
            rank=grade.rank if grade else None,
            z_score=grade.z_score if grade else None,
            total_possible_marks=marks_possible,
        )

    for ranking_payload, current_score, marks_possible in ranking_meta:
        final_marks = ranking_payload["final_marks"]
        ranking_payload["comparison"] = build_marks_comparison(
            current_score,
            score_pool=score_pool,
            rank=final_marks["rank"] if final_marks else None,
            z_score=final_marks["z_score"] if final_marks else None,
            total_possible_marks=marks_possible or total_stage_marks or None,
        )

    ranking.sort(key=lambda item: item["final_marks"]["rank"])
    return {
        "statistics": {
            "student_count": len(students),
            "evaluated_count": len(score_pool),
            "mean_score": average,
            "std_score": std_dev,
            "top_score": top_score,
            "total_possible_marks": total_stage_marks or 10.0,
        },
        "students": rows,
        "rankings": ranking,
        "stage_definitions": [serialize_stage_definition(item) for item in stage_definitions],
        "rubrics": [serialize_scoring_rubric(item) for item in rubrics],
        "continuous_progress": continuous_evaluation_service.summarize_stage_progress(db),
        "master_brief": serialize_master_brief(master_brief_service.get_master_brief(db)),
    }


def finalize_relative_grades(db: Session, evaluate_callback) -> dict:
    stage_definitions = continuous_evaluation_service.list_stages(db)
    total_stage_marks = get_total_stage_marks(stage_definitions)

    students = list(
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
            .order_by(Student.id)
        )
    )

    scored_entries: list[dict] = []
    for student in students:
        latest_project = get_latest_project_track(student)
        latest_by_stage = get_latest_stage_submissions_by_order(latest_project)
        if latest_by_stage:
            total_marks = 0.0
            latest_stage_submission = None
            latest_stage_evaluation = None

            for order in sorted(latest_by_stage):
                stage_submission = latest_by_stage[order]
                stage_evaluation = get_latest_stage_evaluation(stage_submission)
                if not stage_evaluation:
                    stage_evaluation = continuous_evaluation_service.evaluate_stage_submission(db, stage_submission.id)
                total_marks += stage_evaluation.scaled_score
                latest_stage_submission = stage_submission
                latest_stage_evaluation = stage_evaluation

            if latest_stage_submission and latest_stage_evaluation:
                finalized_snapshot = build_stage_score_snapshot(latest_project, total_stage_marks=total_stage_marks)
                scored_entries.append(
                    {
                        "student": student,
                        "submission": latest_stage_submission,
                        "evaluation": latest_stage_evaluation,
                        "score": round(total_marks, 2),
                        "score_out_of": total_stage_marks or round(
                            sum(
                                item.stage.max_marks if item.stage else 0.0
                                for item in latest_by_stage.values()
                            ),
                            2,
                        ),
                        "is_stage_based": True,
                        "stage_breakdown": finalized_snapshot["stage_breakdown"] if finalized_snapshot else [],
                    }
                )
                continue

        latest_submission = get_latest_submission(student)
        if not latest_submission:
            continue

        final_evaluation = get_latest_evaluation(latest_submission, draft=False)
        if not final_evaluation:
            final_evaluation = evaluate_callback(latest_submission, draft=False)

        scored_entries.append(
            {
                "student": student,
                "submission": latest_submission,
                "evaluation": final_evaluation,
                "score": final_evaluation.total_score,
                "score_out_of": 10.0,
                "is_stage_based": False,
            }
        )

    if not scored_entries:
        return {
            "statistics": {
                "student_count": len(students),
                "evaluated_count": 0,
                "mean_score": 0.0,
                "std_score": 0.0,
                "top_score": 0.0,
                "total_possible_marks": total_stage_marks or 10.0,
            },
            "rankings": [],
        }

    scores = [entry["score"] for entry in scored_entries]
    average = mean(scores)
    std_dev = pstdev(scores) if len(scores) > 1 else 0.0
    ranked_entries = sorted(
        scored_entries,
        key=lambda item: (item["score"], item["evaluation"].created_at),
        reverse=True,
    )

    for rank, entry in enumerate(ranked_entries, start=1):
        z_score = 0.0 if std_dev == 0 else round((entry["score"] - average) / std_dev, 4)
        grade = entry["student"].grade or Grade(student_id=entry["student"].id)
        grade.final_score = entry["score"]
        grade.grade = "NA"
        grade.z_score = z_score
        grade.rank = rank
        db.add(grade)

    db.flush()
    db.commit()

    refreshed_students = {
        student.id: student
        for student in db.scalars(
            select(Student)
            .options(
                selectinload(Student.grade),
                selectinload(Student.submissions).selectinload(Submission.evaluations),
                selectinload(Student.progress_projects)
                .selectinload(ProjectTrack.stage_submissions)
                .selectinload(StageSubmission.stage),
                selectinload(Student.progress_projects)
                .selectinload(ProjectTrack.stage_submissions)
                .selectinload(StageSubmission.evaluations),
            )
            .where(Student.id.in_([entry["student"].id for entry in ranked_entries]))
        )
    }
    refreshed_grades = {
        grade.student_id: grade
        for grade in db.scalars(select(Grade).where(Grade.student_id.in_([entry["student"].id for entry in ranked_entries])))
    }

    ranking_payload: list[dict] = []
    for entry in ranked_entries:
        refreshed = refreshed_students[entry["student"].id]
        grade = refreshed_grades.get(entry["student"].id)
        if not grade:
            continue

        ranking_payload.append(
            {
                "student": serialize_student(refreshed),
                "submission": serialize_stage_submission(entry["submission"]) if entry["is_stage_based"] else serialize_submission(entry["submission"]),
                "evaluation": serialize_stage_evaluation(entry["evaluation"]) if entry["is_stage_based"] else serialize_evaluation(entry["evaluation"]),
                "final_marks": build_final_marks_payload(
                    grade.final_score,
                    entry["score_out_of"],
                    rank=grade.rank,
                    z_score=grade.z_score,
                    finalized_at=grade.created_at,
                ),
                "comparison": build_marks_comparison(
                    entry["score"],
                    score_pool=scores,
                    rank=grade.rank,
                    z_score=grade.z_score,
                    total_possible_marks=entry["score_out_of"],
                ),
                "stage_breakdown": entry.get("stage_breakdown", []),
            }
        )

    ranking_payload.sort(key=lambda item: item["final_marks"]["rank"])
    return {
        "statistics": {
            "student_count": len(students),
            "evaluated_count": len(scores),
            "mean_score": round(average, 2),
            "std_score": round(std_dev, 2),
            "top_score": round(max(scores), 2),
            "total_possible_marks": round(max((entry["score_out_of"] for entry in ranked_entries), default=total_stage_marks or 10.0), 2),
        },
        "rankings": ranking_payload,
    }
