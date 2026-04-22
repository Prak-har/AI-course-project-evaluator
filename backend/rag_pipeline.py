from fastapi import HTTPException, status
from openai import APIConnectionError, APIError, AuthenticationError, PermissionDeniedError, RateLimitError
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import Evaluation, Submission
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


class RAGPipeline:
    def ingest_submission(self, submission: Submission) -> dict:
        llm_client.refresh()
        if not llm_client.configured:
            return {"embedded": False, "chunk_count": 0}

        chunks = chunk_text(
            submission.content,
            chunk_size=settings.chunk_word_size,
            overlap=settings.chunk_word_overlap,
        )
        if not chunks:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submission content is empty.")

        try:
            embeddings = llm_client.embed_texts([chunk["text"] for chunk in chunks])
        except (AuthenticationError, PermissionDeniedError, RateLimitError, APIConnectionError, APIError) as exc:
            return {
                "embedded": False,
                "chunk_count": len(chunks),
                "warning": describe_provider_error(exc),
            }
        submission_vector_store.save_submission(submission.id, chunks, embeddings)
        return {"embedded": True, "chunk_count": len(chunks), "warning": None}

    def ensure_submission_embeddings(self, submission: Submission) -> None:
        try:
            metadata = submission_vector_store.load_metadata(submission.id)
            if metadata.get("chunks"):
                return
        except FileNotFoundError:
            pass

        ingestion_result = self.ingest_submission(submission)
        if ingestion_result.get("embedded"):
            return

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ingestion_result.get("warning")
            or "Unable to create embeddings for this submission. Check the Gemini API configuration and try again.",
        )

    def evaluate_submission(self, db: Session, submission: Submission, draft: bool = True) -> Evaluation:
        llm_client.refresh()
        if not llm_client.configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM_API_KEY is not configured. Add a valid provider key in .env before evaluation.",
            )

        topic_validation = master_brief_service.validate_submission_topic(db, submission.content)
        if topic_validation.get("has_master_brief") and not topic_validation.get("accepted", True):
            return self._build_topic_rejection_evaluation(db, submission, topic_validation, draft)

        self.ensure_submission_embeddings(submission)
        active_rubrics = rubric_service.get_applicable_rubrics(db)
        rubric_prompt_payload = [
            {
                "key": rubric.key,
                "name": rubric.name,
                "weight": rubric.weight,
            }
            for rubric in active_rubrics
        ]

        try:
            query_embedding = llm_client.embed_texts([RAG_EVALUATION_QUERY])[0]
        except (AuthenticationError, PermissionDeniedError, RateLimitError, APIConnectionError, APIError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=describe_provider_error(exc),
            ) from exc
        try:
            retrieved_chunks = submission_vector_store.retrieve(
                submission.id,
                query_embedding=query_embedding,
                top_k=settings.retrieval_top_k,
            )
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission embeddings were not found. Re-upload the submission or rebuild the vector index.",
            ) from exc
        if not retrieved_chunks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission embeddings were not found. Re-upload the submission or rebuild the vector index.",
            )

        try:
            features = llm_client.generate_json(
                FEATURE_EXTRACTION_SYSTEM_PROMPT,
                build_feature_extraction_prompt(retrieved_chunks),
            )
            scores = llm_client.generate_json(
                SCORING_SYSTEM_PROMPT,
                build_scoring_prompt(retrieved_chunks, features, rubric_prompt_payload),
            )
            feedback = llm_client.generate_json(
                FEEDBACK_SYSTEM_PROMPT,
                build_feedback_prompt(retrieved_chunks, features, scores),
            )
        except (AuthenticationError, PermissionDeniedError, RateLimitError, APIConnectionError, APIError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=describe_provider_error(exc),
            ) from exc

        normalized_scores = rubric_service.normalize_scores(scores.get("criterion_scores", scores), active_rubrics)
        total_score = rubric_service.compute_weighted_total(normalized_scores, active_rubrics)
        compatibility_scores = rubric_service.build_legacy_compatibility_scores(normalized_scores, total_score)
        weak_sections = self._build_weak_sections(feedback.get("weak_sections", []), retrieved_chunks)
        plagiarism_matches = submission_vector_store.find_similar_submissions(
            submission.id,
            submission_lookup=lambda submission_id: db.get(Submission, submission_id),
            threshold=settings.plagiarism_threshold,
        )

        evaluation = Evaluation(
            submission_id=submission.id,
            innovation_score=compatibility_scores["innovation_score"],
            technical_score=compatibility_scores["technical_score"],
            clarity_score=compatibility_scores["clarity_score"],
            impact_score=compatibility_scores["impact_score"],
            total_score=total_score,
            feedback={
                "strengths": self._normalize_list(feedback.get("strengths")),
                "weaknesses": self._normalize_list(feedback.get("weaknesses")),
                "suggestions": self._normalize_list(feedback.get("suggestions")),
                "future_scope": self._normalize_list(feedback.get("future_scope")),
                "criterion_justifications": self._normalize_text_mapping(
                    scores.get("criterion_justifications", {}),
                    normalized_scores.keys(),
                ),
                "evidence": self._normalize_evidence_mapping(
                    scores.get("evidence", {}),
                    normalized_scores.keys(),
                ),
                "rubric_scores": normalized_scores,
                "rubric_weights": rubric_service.build_weight_snapshot(active_rubrics),
            },
            features=features,
            retrieved_chunks=retrieved_chunks,
            weak_sections=weak_sections,
            plagiarism_matches=plagiarism_matches,
            draft=draft,
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)
        return evaluation

    def _build_topic_rejection_evaluation(
        self,
        db: Session,
        submission: Submission,
        topic_validation: dict,
        draft: bool,
    ) -> Evaluation:
        active_rubrics = rubric_service.get_applicable_rubrics(db)
        excerpt = submission.content[:240] + ("..." if len(submission.content) > 240 else "")
        rejection_reason = str(topic_validation.get("reason", "Submission topic is outside the approved scope."))
        matched_topics = topic_validation.get("matched_topics") or []
        rubric_scores = {rubric.key: 0.0 for rubric in active_rubrics}
        compatibility_scores = rubric_service.build_legacy_compatibility_scores(rubric_scores, 0.0)
        justifications = {rubric.key: rejection_reason for rubric in active_rubrics}
        evidence = {rubric.key: [] for rubric in active_rubrics}

        evaluation = Evaluation(
            submission_id=submission.id,
            innovation_score=compatibility_scores["innovation_score"],
            technical_score=compatibility_scores["technical_score"],
            clarity_score=compatibility_scores["clarity_score"],
            impact_score=compatibility_scores["impact_score"],
            total_score=0.0,
            feedback={
                "strengths": matched_topics or ["Submission was processed, but no approved topic match was established."],
                "weaknesses": [rejection_reason],
                "suggestions": [
                    "Resubmit the project using a topic explicitly accepted in the teacher master brief.",
                    "Align the title, objective, and implementation details with the approved course themes before resubmitting.",
                ],
                "future_scope": ["Choose an approved topic from the master brief and rebuild the submission around that scope."],
                "criterion_justifications": justifications,
                "evidence": evidence,
                "rubric_scores": rubric_scores,
                "rubric_weights": rubric_service.build_weight_snapshot(active_rubrics),
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
            retrieved_chunks=[{"chunk_id": 0, "score": 1.0, "text": excerpt, "start_word": 0, "end_word": min(len(submission.content.split()), 80)}],
            weak_sections=[
                {
                    "criterion": "topic_alignment",
                    "chunk_id": 0,
                    "reason": rejection_reason,
                    "excerpt": excerpt or "Insufficient data",
                }
            ],
            plagiarism_matches=[],
            draft=draft,
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)
        return evaluation

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

        for item in items or []:
            chunk_id = item.get("chunk_id")
            chunk = chunk_map.get(chunk_id)
            excerpt = "Insufficient data"
            if chunk:
                excerpt = chunk["text"][:400] + ("..." if len(chunk["text"]) > 400 else "")

            normalized.append(
                {
                    "criterion": str(item.get("criterion", "general")),
                    "chunk_id": chunk_id,
                    "reason": str(item.get("reason", "Insufficient data")),
                    "excerpt": excerpt,
                }
            )

        return normalized


rag_pipeline = RAGPipeline()
