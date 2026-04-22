import json
from pathlib import Path

from fastapi import HTTPException, status
from openai import APIConnectionError, APIError, AuthenticationError, PermissionDeniedError, RateLimitError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import MasterBrief
from backend.services.llm_client import describe_provider_error, llm_client


MASTER_BRIEF_VALIDATION_SYSTEM_PROMPT = """
You are checking whether a student project submission matches the allowed course project topics.

Rules:
- ONLY use the provided master brief content and student submission content.
- If the master brief does not clearly define acceptable topics, return accepted=true and reason "Insufficient data".
- Never invent missing requirements or topics.
- Return valid JSON only.
""".strip()


def _truncate_text(value: str, limit: int = 6000) -> str:
    cleaned = " ".join((value or "").split()).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def serialize_master_brief(master_brief: MasterBrief | None) -> dict | None:
    if not master_brief:
        return None
    return {
        "id": master_brief.id,
        "title": master_brief.title,
        "original_filename": master_brief.original_filename,
        "file_type": master_brief.file_type,
        "storage_path": master_brief.storage_path,
        "content_preview": _truncate_text(master_brief.content, limit=260),
        "created_at": master_brief.created_at,
        "updated_at": master_brief.updated_at,
    }


class MasterBriefService:
    def get_master_brief(self, db: Session) -> MasterBrief | None:
        return db.scalar(select(MasterBrief).order_by(MasterBrief.updated_at.desc(), MasterBrief.created_at.desc()))

    def save_master_brief(
        self,
        db: Session,
        *,
        title: str,
        content: str,
        file_type: str,
        original_filename: str | None,
        storage_path: str | None,
    ) -> MasterBrief:
        existing = self.get_master_brief(db)
        if existing and existing.storage_path and existing.storage_path != storage_path:
            old_path = Path(existing.storage_path)
            if old_path.exists():
                try:
                    old_path.unlink()
                except OSError:
                    pass

        master_brief = existing or MasterBrief()
        master_brief.title = title.strip() or "Course Master Brief"
        master_brief.content = content
        master_brief.file_type = file_type
        master_brief.original_filename = original_filename
        master_brief.storage_path = storage_path
        db.add(master_brief)
        db.commit()
        db.refresh(master_brief)
        return master_brief

    def validate_submission_topic(self, db: Session, submission_text: str) -> dict:
        master_brief = self.get_master_brief(db)
        if not master_brief:
            return {
                "has_master_brief": False,
                "accepted": True,
                "reason": "No master brief uploaded.",
                "matched_topics": [],
            }

        llm_client.refresh()
        if not llm_client.configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM_API_KEY is not configured. Add a valid provider key in .env before evaluation.",
            )

        prompt = f"""
Master brief:
{_truncate_text(master_brief.content)}

Student submission:
{_truncate_text(submission_text)}

Return JSON with this exact structure:
{{
  "accepted": true,
  "reason": "string",
  "matched_topics": ["topic 1", "topic 2"]
}}
""".strip()

        try:
            result = llm_client.generate_json(MASTER_BRIEF_VALIDATION_SYSTEM_PROMPT, prompt)
        except (AuthenticationError, PermissionDeniedError, RateLimitError, APIConnectionError, APIError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=describe_provider_error(exc),
            ) from exc

        accepted = bool(result.get("accepted", True))
        matched_topics = result.get("matched_topics") if isinstance(result.get("matched_topics"), list) else []
        reason = str(result.get("reason", "Insufficient data")).strip() or "Insufficient data"
        return {
            "has_master_brief": True,
            "accepted": accepted,
            "reason": reason,
            "matched_topics": [str(item).strip() for item in matched_topics if str(item).strip()],
            "master_brief_title": master_brief.title,
        }


master_brief_service = MasterBriefService()
