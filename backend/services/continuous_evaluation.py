import json
import shutil
from pathlib import Path

import numpy as np
from fastapi import HTTPException, status
from openai import APIConnectionError, APIError, AuthenticationError, PermissionDeniedError, RateLimitError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.config import get_settings
from backend.models import Evaluation, LegacySubmissionStageLink, ProjectTrack, StageDefinition, StageEvaluation, StageSubmission, Student, Submission
from backend.prompts.evaluation_prompts import (
    FEATURE_EXTRACTION_SYSTEM_PROMPT,
    FEEDBACK_SYSTEM_PROMPT,
    RAG_EVALUATION_QUERY,
    SCORING_SYSTEM_PROMPT,
    build_feature_extraction_prompt,
    build_feedback_prompt,
    build_scoring_prompt,
)
from backend.services.ingestion import chunk_text
from backend.services.llm_client import describe_provider_error, llm_client
from backend.services.master_brief import master_brief_service
from backend.services.rubrics import rubric_service
from backend.services.vector_store import submission_vector_store


settings = get_settings()

FOLLOW_THROUGH_SYSTEM_PROMPT = """
You are checking whether a student addressed the recommendations from earlier project stages.

Rules:
- ONLY use the provided previous stage recommendations and the current stage content.
- Do not assume work was completed unless the current stage clearly supports it.
- Return valid JSON only.
""".strip()


class ContinuousEvaluationService:
    def list_stages(self, db: Session) -> list[StageDefinition]:
        return list(
            db.scalars(
                select(StageDefinition)
                .options(selectinload(StageDefinition.stage_submissions))
                .order_by(StageDefinition.stage_order)
            )
        )

    def _load_project_for_stage_submission(self, db: Session, student_id: int, title: str) -> ProjectTrack | None:
        normalized_title = title.strip() or "Untitled Continuous Project"
        return db.scalar(
            select(ProjectTrack)
            .options(
                selectinload(ProjectTrack.stage_submissions).selectinload(StageSubmission.stage),
                selectinload(ProjectTrack.stage_submissions).selectinload(StageSubmission.evaluations),
                selectinload(ProjectTrack.student).selectinload(Student.grade),
            )
            .where(ProjectTrack.student_id == student_id, func.lower(ProjectTrack.title) == normalized_title.lower())
            .order_by(ProjectTrack.created_at.desc())
        )

    def _latest_stage_submissions_by_order(self, project: ProjectTrack | None) -> dict[int, StageSubmission]:
        if not project:
            return {}

        latest_by_stage: dict[int, StageSubmission] = {}
        for submission in project.stage_submissions:
            order = submission.stage.stage_order if submission.stage else 0
            existing = latest_by_stage.get(order)
            if not existing or submission.created_at > existing.created_at:
                latest_by_stage[order] = submission
        return latest_by_stage

    def validate_stage_submission(
        self,
        db: Session,
        *,
        student_id: int,
        project_title: str,
        stage_id: int,
    ) -> dict:
        student = db.get(Student, student_id)
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

        stage = db.get(StageDefinition, stage_id)
        if not stage:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found.")

        normalized_title = project_title.strip() or "Untitled Continuous Project"
        project = self._load_project_for_stage_submission(db, student_id, normalized_title)
        latest_by_stage = self._latest_stage_submissions_by_order(project)
        existing_orders = set(latest_by_stage)

        if project and stage.stage_order in existing_orders:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{stage.name} is already submitted for this project. Delete that stage submission first if you need to replace it.",
            )

        if not project and stage.stage_order != 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Start with Stage 1 for a new project before uploading later stages.",
            )

        missing_prior_stage = next((order for order in range(1, stage.stage_order) if order not in existing_orders), None)
        if missing_prior_stage is not None:
            required_stage = db.scalar(select(StageDefinition).where(StageDefinition.stage_order == missing_prior_stage))
            required_name = required_stage.name if required_stage else f"Stage {missing_prior_stage}"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Submit {required_name} before uploading {stage.name}. Stage submissions must follow chronology.",
            )

        return {
            "student": student,
            "stage": stage,
            "project": project,
            "normalized_title": normalized_title,
            "latest_by_stage": latest_by_stage,
        }

    def update_stage(self, db: Session, stage_id: int, name: str, max_marks: float) -> StageDefinition:
        stage = db.scalar(
            select(StageDefinition)
            .options(selectinload(StageDefinition.stage_submissions).selectinload(StageSubmission.evaluations))
            .where(StageDefinition.id == stage_id)
        )
        if not stage:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found.")

        stage.name = name.strip() or f"Stage {stage.stage_order}"
        stage.max_marks = round(max(float(max_marks), 1.0), 2)
        for submission in stage.stage_submissions:
            for evaluation in submission.evaluations:
                evaluation.max_marks = stage.max_marks
                evaluation.scaled_score = round((evaluation.raw_total_score / 10.0) * stage.max_marks, 2)
                if evaluation.context_snapshot:
                    evaluation.context_snapshot["max_marks"] = stage.max_marks
                db.add(evaluation)
        db.add(stage)
        db.commit()
        db.refresh(stage)
        return stage

    def create_stage(self, db: Session, name: str, max_marks: float) -> StageDefinition:
        normalized_name = name.strip() or "New Stage"
        next_order = (db.scalar(select(func.max(StageDefinition.stage_order))) or 0) + 1
        stage = StageDefinition(
            name=normalized_name,
            stage_order=next_order,
            max_marks=round(max(float(max_marks), 1.0), 2),
        )
        db.add(stage)
        db.commit()
        db.refresh(stage)
        return stage

    def delete_stage(self, db: Session, stage_id: int) -> dict:
        stage = db.scalar(
            select(StageDefinition)
            .options(selectinload(StageDefinition.stage_submissions))
            .where(StageDefinition.id == stage_id)
        )
        if not stage:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found.")

        max_stage_order = db.scalar(select(func.max(StageDefinition.stage_order))) or stage.stage_order
        if stage.stage_order != max_stage_order:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only the last stage can be deleted. Delete higher-order stages first to keep chronology stable.",
            )
        if stage.stage_submissions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This stage already has submissions and cannot be deleted.",
            )

        db.delete(stage)
        db.commit()
        return {"deleted_stage_id": stage_id, "message": "Stage deleted successfully."}

    def migrate_legacy_submissions(self, db: Session) -> None:
        stage_one = db.scalar(select(StageDefinition).where(StageDefinition.stage_order == 1))
        if not stage_one:
            return

        linked_submission_ids = {
            submission_id
            for submission_id in db.scalars(select(LegacySubmissionStageLink.submission_id))
        }

        submissions = list(
            db.scalars(
                select(Submission)
                .options(selectinload(Submission.evaluations), selectinload(Submission.student))
                .order_by(Submission.created_at.asc())
            )
        )
        changed = False

        for submission in submissions:
            if submission.id in linked_submission_ids:
                continue

            project = self.find_or_create_project(db, submission.student_id, submission.title)
            stage_submission = StageSubmission(
                project_id=project.id,
                stage_id=stage_one.id,
                original_filename=submission.original_filename,
                file_type=submission.file_type,
                storage_path=submission.storage_path,
                content=submission.content,
                created_at=submission.created_at,
            )
            db.add(stage_submission)
            db.flush()

            for evaluation in submission.evaluations:
                stage_evaluation = StageEvaluation(
                    stage_submission_id=stage_submission.id,
                    raw_total_score=evaluation.total_score,
                    scaled_score=round((evaluation.total_score / 10.0) * stage_one.max_marks, 2),
                    max_marks=stage_one.max_marks,
                    feedback=evaluation.feedback or {},
                    features=evaluation.features or {},
                    context_snapshot={
                        "project_title": submission.title,
                        "stage_name": stage_one.name,
                        "stage_order": stage_one.stage_order,
                        "max_marks": stage_one.max_marks,
                        "migrated_from_submission_id": submission.id,
                        "prior_stages": [],
                    },
                    retrieved_chunks=evaluation.retrieved_chunks or [],
                    weak_sections=evaluation.weak_sections or [],
                    created_at=evaluation.created_at,
                )
                db.add(stage_evaluation)

            db.add(
                LegacySubmissionStageLink(
                    submission_id=submission.id,
                    stage_submission_id=stage_submission.id,
                )
            )
            changed = True

        if changed:
            db.commit()

    def find_or_create_project(self, db: Session, student_id: int, title: str) -> ProjectTrack:
        normalized_title = title.strip() or "Untitled Continuous Project"
        project = db.scalar(
            select(ProjectTrack)
            .where(ProjectTrack.student_id == student_id, func.lower(ProjectTrack.title) == normalized_title.lower())
            .order_by(ProjectTrack.created_at.desc())
        )
        if project:
            return project

        project = ProjectTrack(student_id=student_id, title=normalized_title)
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    def save_stage_submission(
        self,
        db: Session,
        *,
        student_id: int,
        project_title: str,
        stage_id: int,
        content: str,
        file_type: str,
        original_filename: str | None,
        storage_path: str | None,
    ) -> StageSubmission:
        validation = self.validate_stage_submission(
            db,
            student_id=student_id,
            project_title=project_title,
            stage_id=stage_id,
        )
        stage = validation["stage"]
        project = validation["project"] or self.find_or_create_project(db, student_id, validation["normalized_title"])
        submission = StageSubmission(
            project_id=project.id,
            stage_id=stage.id,
            original_filename=original_filename,
            file_type=file_type,
            storage_path=storage_path,
            content=content,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission

    def get_stage_submission(self, db: Session, stage_submission_id: int) -> StageSubmission:
        submission = db.scalar(
            select(StageSubmission)
            .options(
                selectinload(StageSubmission.stage),
                selectinload(StageSubmission.project)
                .selectinload(ProjectTrack.student)
                .selectinload(Student.grade),
                selectinload(StageSubmission.project)
                .selectinload(ProjectTrack.stage_submissions)
                .selectinload(StageSubmission.stage),
                selectinload(StageSubmission.project)
                .selectinload(ProjectTrack.stage_submissions)
                .selectinload(StageSubmission.evaluations),
            )
            .where(StageSubmission.id == stage_submission_id)
        )
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage submission not found.")
        return submission

    def delete_stage_submission(self, db: Session, stage_submission_id: int, student_id: int) -> dict:
        submission = db.scalar(
            select(StageSubmission)
            .options(
                selectinload(StageSubmission.project).selectinload(ProjectTrack.student),
                selectinload(StageSubmission.project).selectinload(ProjectTrack.stage_submissions).selectinload(StageSubmission.stage),
            )
            .where(StageSubmission.id == stage_submission_id)
        )
        if not submission or submission.project.student_id != student_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage submission not found.")

        current_stage_order = submission.stage.stage_order if submission.stage else 0
        later_stage_exists = any(
            item.id != stage_submission_id and item.stage and item.stage.stage_order > current_stage_order
            for item in submission.project.stage_submissions
        )
        if later_stage_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Delete later stages first. Stage deletions must also follow reverse chronology.",
            )

        link = db.scalar(
            select(LegacySubmissionStageLink).where(LegacySubmissionStageLink.stage_submission_id == stage_submission_id)
        )
        legacy_submission = db.get(Submission, link.submission_id) if link else None

        stage_storage_path = Path(submission.storage_path) if submission.storage_path else None
        legacy_storage_path = Path(legacy_submission.storage_path) if legacy_submission and legacy_submission.storage_path else None
        legacy_submission_id = legacy_submission.id if legacy_submission else None
        student_name = submission.project.student.name
        project = submission.project
        remaining_stage_ids = [item.id for item in project.stage_submissions if item.id != stage_submission_id]

        if link:
            db.delete(link)
        if legacy_submission:
            db.delete(legacy_submission)
        db.delete(submission)

        if not remaining_stage_ids:
            db.delete(project)

        db.commit()

        for path in [stage_storage_path, legacy_storage_path]:
            if path and path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass

        if legacy_submission_id:
            report_path = settings.reports_dir / f"submission_{legacy_submission_id}_report.pdf"
            if report_path.exists():
                try:
                    report_path.unlink()
                except OSError:
                    pass
            faiss_path = submission_vector_store.base_dir / str(legacy_submission_id)
            if faiss_path.exists():
                try:
                    shutil.rmtree(faiss_path, ignore_errors=True)
                except OSError:
                    pass

        return {
            "deleted_stage_submission_id": stage_submission_id,
            "deleted_student_id": student_id,
            "deleted_student_name": student_name,
            "message": "Stage submission deleted successfully.",
        }

    def evaluate_stage_submission(self, db: Session, stage_submission_id: int) -> StageEvaluation:
        submission = self.get_stage_submission(db, stage_submission_id)
        llm_client.refresh()
        if not llm_client.configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM_API_KEY is not configured. Add a valid provider key in .env before stage evaluation.",
            )

        topic_validation = master_brief_service.validate_submission_topic(db, submission.content)
        if topic_validation.get("has_master_brief") and not topic_validation.get("accepted", True):
            return self._build_topic_rejection_stage_evaluation(db, submission, topic_validation)

        active_rubrics = rubric_service.get_applicable_rubrics(db, stage_order=submission.stage.stage_order)
        general_rubrics = [rubric for rubric in active_rubrics if not rubric.later_stage_only]
        follow_through_rubric = next((rubric for rubric in active_rubrics if rubric.later_stage_only), None)
        rubric_prompt_payload = [
            {
                "key": rubric.key,
                "name": rubric.name,
                "weight": rubric.weight,
            }
            for rubric in general_rubrics
        ]

        try:
            retrieved_chunks = self._retrieve_relevant_chunks(submission.content)
            prior_context = self._build_prior_stage_context(submission)
            feature_prompt = self._build_continuous_prompt(
                build_feature_extraction_prompt(retrieved_chunks),
                submission,
                prior_context,
            )
            features = llm_client.generate_json(FEATURE_EXTRACTION_SYSTEM_PROMPT, feature_prompt)
            carry_forward = self._assess_previous_recommendations(submission, prior_context, retrieved_chunks)

            scoring_prompt = self._build_continuous_prompt(
                build_scoring_prompt(retrieved_chunks, features, rubric_prompt_payload),
                submission,
                prior_context,
            )
            scores = llm_client.generate_json(SCORING_SYSTEM_PROMPT, scoring_prompt)

            feedback_prompt = self._build_continuous_prompt(
                build_feedback_prompt(retrieved_chunks, features, scores),
                submission,
                prior_context,
            )
            feedback = llm_client.generate_json(FEEDBACK_SYSTEM_PROMPT, feedback_prompt)
        except (AuthenticationError, PermissionDeniedError, RateLimitError, APIConnectionError, APIError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=describe_provider_error(exc),
            ) from exc

        normalized_scores = rubric_service.normalize_scores(scores.get("criterion_scores", scores), general_rubrics)
        if follow_through_rubric and submission.stage.stage_order > 1 and prior_context:
            normalized_scores[follow_through_rubric.key] = rubric_service.clamp_score(carry_forward.get("score"))

        raw_total_score = rubric_service.compute_weighted_total(normalized_scores, active_rubrics)
        scaled_score = round((raw_total_score / 10.0) * submission.stage.max_marks, 2)
        weight_snapshot = rubric_service.build_weight_snapshot(active_rubrics)
        criterion_justifications = self._normalize_text_mapping(
            scores.get("criterion_justifications", {}),
            normalized_scores.keys(),
        )
        evidence = self._normalize_evidence_mapping(scores.get("evidence", {}), normalized_scores.keys())
        if follow_through_rubric and follow_through_rubric.key in normalized_scores:
            criterion_justifications[follow_through_rubric.key] = carry_forward.get("summary", "Insufficient data")
            evidence[follow_through_rubric.key] = []

        evaluation = StageEvaluation(
            stage_submission_id=submission.id,
            raw_total_score=raw_total_score,
            scaled_score=scaled_score,
            max_marks=submission.stage.max_marks,
            feedback={
                "strengths": self._normalize_list(feedback.get("strengths")),
                "weaknesses": self._normalize_list(feedback.get("weaknesses")),
                "suggestions": self._normalize_list(feedback.get("suggestions")),
                "future_scope": self._normalize_list(feedback.get("future_scope")),
                "carry_forward": carry_forward,
                "criterion_justifications": criterion_justifications,
                "evidence": evidence,
                "rubric_scores": normalized_scores,
                "rubric_weights": weight_snapshot,
            },
            features=features,
            context_snapshot={
                "project_title": submission.project.title,
                "stage_name": submission.stage.name,
                "stage_order": submission.stage.stage_order,
                "max_marks": submission.stage.max_marks,
                "rubrics": weight_snapshot,
                "prior_stages": prior_context,
                "progress_on_previous_feedback": carry_forward,
            },
            retrieved_chunks=retrieved_chunks,
            weak_sections=self._build_weak_sections(feedback.get("weak_sections", []), retrieved_chunks),
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)
        return evaluation

    def _build_topic_rejection_stage_evaluation(
        self,
        db: Session,
        submission: StageSubmission,
        topic_validation: dict,
    ) -> StageEvaluation:
        active_rubrics = rubric_service.get_applicable_rubrics(db, stage_order=submission.stage.stage_order)
        rejection_reason = str(topic_validation.get("reason", "Submission topic is outside the approved scope."))
        matched_topics = topic_validation.get("matched_topics") or []
        scaled_score = 0.0
        raw_total_score = 0.0
        excerpt = submission.content[:240] + ("..." if len(submission.content) > 240 else "")
        rubric_scores = {rubric.key: raw_total_score for rubric in active_rubrics}
        weight_snapshot = rubric_service.build_weight_snapshot(active_rubrics)
        justifications = {rubric.key: rejection_reason for rubric in rubric_scores}
        evidence = {rubric.key: [] for rubric in rubric_scores}

        evaluation = StageEvaluation(
            stage_submission_id=submission.id,
            raw_total_score=raw_total_score,
            scaled_score=scaled_score,
            max_marks=submission.stage.max_marks,
            feedback={
                "strengths": matched_topics or ["Submission was processed, but no approved topic match was established."],
                "weaknesses": [rejection_reason],
                "suggestions": [
                    "Resubmit this stage using a topic explicitly accepted in the teacher master brief.",
                    "Make the problem statement and implementation align with the approved course topics before the next evaluation.",
                ],
                "future_scope": ["Rework the project around an approved topic and upload the corrected stage again."],
                "carry_forward": {
                    "summary": "Previous recommendations were not evaluated because the submission failed the master-brief topic check.",
                    "addressed_items": [],
                    "pending_items": [],
                    "score": raw_total_score,
                },
                "criterion_justifications": justifications,
                "evidence": evidence,
                "rubric_scores": rubric_scores,
                "rubric_weights": weight_snapshot,
                "topic_validation": topic_validation,
            },
            features={
                "innovation": {"summary": "Rejected due to topic mismatch", "evidence_chunk_ids": []},
                "technologies": matched_topics,
                "complexity": {
                    "summary": "Rejected due to topic mismatch",
                    "level": "Insufficient data",
                    "evidence_chunk_ids": [],
                },
                "topic_validation": topic_validation,
            },
            context_snapshot={
                "project_title": submission.project.title,
                "stage_name": submission.stage.name,
                "stage_order": submission.stage.stage_order,
                "max_marks": submission.stage.max_marks,
                "rubrics": weight_snapshot,
                "prior_stages": self._build_prior_stage_context(submission),
                "progress_on_previous_feedback": {
                    "summary": "Previous recommendations were not evaluated because the submission failed the master-brief topic check.",
                    "addressed_items": [],
                    "pending_items": [],
                    "score": raw_total_score,
                },
                "topic_validation": topic_validation,
            },
            retrieved_chunks=[{"chunk_id": 0, "score": 1.0, "text": excerpt, "start_word": 0, "end_word": min(len(submission.content.split()), 80)}],
            weak_sections=[
                {
                    "criterion": "topic_alignment",
                    "chunk_id": 0,
                    "reason": rejection_reason,
                    "excerpt": excerpt or "Insufficient data",
                }
            ],
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)
        return evaluation

    def _build_continuous_prompt(self, base_prompt: str, submission: StageSubmission, prior_context: list[dict]) -> str:
        context_json = json.dumps(prior_context, indent=2)
        return f"""
Continuous evaluation metadata:
- Project title: {submission.project.title}
- Student: {submission.project.student.name}
- Current stage: {submission.stage.name}
- Stage order: {submission.stage.stage_order}
- Max marks for this stage: {submission.stage.max_marks}

Previous stage context for reference:
{context_json if prior_context else "No prior stage context available."}

Important:
- Use previous stage context only to understand continuity and progress.
- Score the current stage using the current stage evidence provided in the retrieved chunks.
- Explicitly check whether the student addressed earlier weaknesses and suggestions when the current stage provides evidence about them.
- If important earlier recommendations are still missing in the current stage, reflect that gap in the marks and feedback for this stage.
- Mention "Insufficient data" if the current stage does not demonstrate enough evidence.

{base_prompt}
""".strip()

    def _retrieve_relevant_chunks(self, content: str) -> list[dict]:
        chunks = chunk_text(
            content,
            chunk_size=settings.chunk_word_size,
            overlap=settings.chunk_word_overlap,
        )
        if not chunks:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stage content is empty.")
        if len(chunks) <= settings.retrieval_top_k:
            return [{**chunk, "score": 1.0} for chunk in chunks]

        embeddings = llm_client.embed_texts([chunk["text"] for chunk in chunks] + [RAG_EVALUATION_QUERY])
        query_vector = np.asarray(embeddings[-1], dtype="float32")
        query_norm = float(np.linalg.norm(query_vector)) or 1.0

        ranked: list[dict] = []
        for chunk, vector in zip(chunks, embeddings[:-1], strict=False):
            chunk_vector = np.asarray(vector, dtype="float32")
            chunk_norm = float(np.linalg.norm(chunk_vector)) or 1.0
            score = float(np.dot(chunk_vector, query_vector) / (chunk_norm * query_norm))
            ranked.append({**chunk, "score": round(score, 4)})

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[: settings.retrieval_top_k]

    def _build_prior_stage_context(self, submission: StageSubmission) -> list[dict]:
        latest_by_stage: dict[int, StageSubmission] = {}
        current_order = submission.stage.stage_order

        for stage_submission in submission.project.stage_submissions:
            order = stage_submission.stage.stage_order
            if order >= current_order or stage_submission.id == submission.id:
                continue
            existing = latest_by_stage.get(order)
            if not existing or (stage_submission.created_at and existing.created_at and stage_submission.created_at > existing.created_at):
                latest_by_stage[order] = stage_submission

        context: list[dict] = []
        for order in sorted(latest_by_stage):
            stage_submission = latest_by_stage[order]
            latest_evaluation = stage_submission.evaluations[0] if stage_submission.evaluations else None
            context.append(
                {
                    "stage_name": stage_submission.stage.name,
                    "stage_order": stage_submission.stage.stage_order,
                    "max_marks": latest_evaluation.max_marks if latest_evaluation else stage_submission.stage.max_marks,
                    "scaled_score": latest_evaluation.scaled_score if latest_evaluation else None,
                    "strengths": (latest_evaluation.feedback or {}).get("strengths", []) if latest_evaluation else [],
                    "weaknesses": (latest_evaluation.feedback or {}).get("weaknesses", []) if latest_evaluation else [],
                    "suggestions": (latest_evaluation.feedback or {}).get("suggestions", []) if latest_evaluation else [],
                    "content_excerpt": stage_submission.content[:280] + ("..." if len(stage_submission.content) > 280 else ""),
                }
            )
        return context

    def summarize_stage_progress(self, db: Session) -> list[dict]:
        projects = list(
            db.scalars(
                select(ProjectTrack)
                .options(
                    selectinload(ProjectTrack.student),
                    selectinload(ProjectTrack.stage_submissions).selectinload(StageSubmission.stage),
                    selectinload(ProjectTrack.stage_submissions).selectinload(StageSubmission.evaluations),
                )
                .order_by(ProjectTrack.created_at.desc())
            )
        )

        rows: list[dict] = []
        for project in projects:
            latest_by_stage: dict[int, StageSubmission] = {}
            for submission in project.stage_submissions:
                order = submission.stage.stage_order
                existing = latest_by_stage.get(order)
                if not existing or (submission.created_at and existing.created_at and submission.created_at > existing.created_at):
                    latest_by_stage[order] = submission

            for order in sorted(latest_by_stage):
                submission = latest_by_stage[order]
                evaluation = submission.evaluations[0] if submission.evaluations else None
                rows.append(
                    {
                        "project_id": project.id,
                        "project_title": project.title,
                        "student": {
                            "id": project.student.id,
                            "name": project.student.name,
                            "email": project.student.email,
                        },
                        "stage_submission_id": submission.id,
                        "stage": {
                            "id": submission.stage.id,
                            "name": submission.stage.name,
                            "stage_order": submission.stage.stage_order,
                            "max_marks": submission.stage.max_marks,
                        },
                        "latest_score": evaluation.scaled_score if evaluation else None,
                        "raw_total_score": evaluation.raw_total_score if evaluation else None,
                        "feedback": evaluation.feedback if evaluation else {},
                        "created_at": submission.created_at,
                    }
                )
        return rows

    def _assess_previous_recommendations(self, submission: StageSubmission, prior_context: list[dict], retrieved_chunks: list[dict]) -> dict:
        if not prior_context:
            return {
                "summary": "No previous stage recommendations to compare yet.",
                "addressed_items": [],
                "pending_items": [],
                "score": 10.0,
            }

        previous_suggestions = [
            {
                "stage_name": item.get("stage_name"),
                "stage_order": item.get("stage_order"),
                "suggestions": item.get("suggestions", []),
            }
            for item in prior_context
        ]
        prompt = f"""
Previous stage recommendations:
{json.dumps(previous_suggestions, indent=2)}

Current stage retrieved chunks:
{json.dumps(retrieved_chunks, indent=2)}

Return JSON with this exact structure:
{{
  "score": 1,
  "summary": "string",
  "addressed_items": ["string"],
  "pending_items": ["string"]
}}
""".strip()

        result = llm_client.generate_json(FOLLOW_THROUGH_SYSTEM_PROMPT, prompt)
        return {
            "score": rubric_service.clamp_score(result.get("score")),
            "summary": str(result.get("summary", "Insufficient data")).strip() or "Insufficient data",
            "addressed_items": self._normalize_list(result.get("addressed_items")),
            "pending_items": self._normalize_list(result.get("pending_items")),
        }

    def _normalize_list(self, value: object) -> list[str]:
        if isinstance(value, list):
            normalized = [str(item).strip() for item in value if str(item).strip()]
            return normalized or ["Insufficient data"]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return ["Insufficient data"]

    def _normalize_text_mapping(self, value: object, keys) -> dict[str, str]:
        raw = value if isinstance(value, dict) else {}
        normalized: dict[str, str] = {}
        for key in keys:
            item = raw.get(key, "Insufficient data")
            normalized[key] = str(item).strip() or "Insufficient data"
        return normalized

    def _normalize_evidence_mapping(self, value: object, keys) -> dict[str, list[int]]:
        raw = value if isinstance(value, dict) else {}
        normalized: dict[str, list[int]] = {}
        for key in keys:
            item = raw.get(key, [])
            if isinstance(item, list):
                chunk_ids: list[int] = []
                for chunk_id in item:
                    try:
                        chunk_ids.append(int(chunk_id))
                    except (TypeError, ValueError):
                        continue
                normalized[key] = chunk_ids
            else:
                normalized[key] = []
        return normalized

    def _build_weak_sections(self, items: list[dict], retrieved_chunks: list[dict]) -> list[dict]:
        chunk_map = {chunk["chunk_id"]: chunk for chunk in retrieved_chunks}
        normalized: list[dict] = []
        seen_keys: set[tuple[str, int | None]] = set()

        for item in items or []:
            criterion = str(item.get("criterion", "general"))
            chunk_id = item.get("chunk_id")
            dedupe_key = (criterion, chunk_id)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            chunk = chunk_map.get(chunk_id)
            excerpt = "Insufficient data"
            if chunk:
                excerpt = chunk["text"][:240] + ("..." if len(chunk["text"]) > 240 else "")

            normalized.append(
                {
                    "criterion": criterion,
                    "chunk_id": chunk_id,
                    "reason": str(item.get("reason", "Insufficient data")),
                    "excerpt": excerpt,
                }
            )

        return normalized


continuous_evaluation_service = ContinuousEvaluationService()
