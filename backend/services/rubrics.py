import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import ScoringRubric


DEFAULT_RUBRICS = [
    {
        "key": "innovation",
        "name": "Innovation",
        "weight": 30.0,
        "display_order": 1,
        "later_stage_only": False,
    },
    {
        "key": "technical_depth",
        "name": "Technical Depth",
        "weight": 30.0,
        "display_order": 2,
        "later_stage_only": False,
    },
    {
        "key": "clarity",
        "name": "Clarity",
        "weight": 20.0,
        "display_order": 3,
        "later_stage_only": False,
    },
    {
        "key": "impact",
        "name": "Impact",
        "weight": 20.0,
        "display_order": 4,
        "later_stage_only": False,
    },
    {
        "key": "recommendation_follow_through",
        "name": "Previous Recommendation Follow-through",
        "weight": 10.0,
        "display_order": 5,
        "later_stage_only": True,
    },
]


class RubricService:
    def list_rubrics(self, db: Session) -> list[ScoringRubric]:
        return list(db.scalars(select(ScoringRubric).order_by(ScoringRubric.display_order, ScoringRubric.id)))

    def get_applicable_rubrics(self, db: Session, *, stage_order: int | None = None) -> list[ScoringRubric]:
        rubrics = self.list_rubrics(db)
        applicable: list[ScoringRubric] = []
        for rubric in rubrics:
            if rubric.weight <= 0:
                continue
            if rubric.later_stage_only and (stage_order is None or stage_order <= 1):
                continue
            applicable.append(rubric)
        if not applicable:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No applicable scoring rubrics are configured. Add a rubric with positive weight from the teacher dashboard.",
            )
        return applicable

    def get_base_rubrics(self, db: Session) -> list[ScoringRubric]:
        rubrics = [rubric for rubric in self.list_rubrics(db) if not rubric.later_stage_only and rubric.weight > 0]
        if not rubrics:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="At least one base rubric with positive weight is required.",
            )
        return rubrics

    def get_later_stage_rubric(self, db: Session) -> ScoringRubric | None:
        return db.scalar(
            select(ScoringRubric)
            .where(ScoringRubric.later_stage_only.is_(True))
            .order_by(ScoringRubric.display_order, ScoringRubric.id)
        )

    def create_rubric(self, db: Session, *, name: str, weight: float, later_stage_only: bool) -> ScoringRubric:
        normalized_name = name.strip() or "New Rubric"
        current = self.list_rubrics(db)
        if later_stage_only and any(item.later_stage_only for item in current):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only one later-stage-only rubric is supported right now. Update the existing follow-through rubric instead of adding another one.",
            )

        rubric = ScoringRubric(
            key=self._build_unique_key(normalized_name, {item.key for item in current}),
            name=normalized_name,
            weight=self._normalize_weight(weight),
            display_order=(max((item.display_order for item in current), default=0) + 1),
            later_stage_only=bool(later_stage_only),
        )
        db.add(rubric)
        db.flush()
        self._validate_rubric_set(db, current + [rubric])
        db.commit()
        db.refresh(rubric)
        return rubric

    def update_rubric(self, db: Session, rubric_id: int, *, name: str, weight: float, later_stage_only: bool) -> ScoringRubric:
        rubric = db.get(ScoringRubric, rubric_id)
        if not rubric:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found.")

        rubrics = self.list_rubrics(db)
        if later_stage_only and any(item.id != rubric_id and item.later_stage_only for item in rubrics):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only one later-stage-only rubric is supported right now.",
            )

        rubric.name = name.strip() or rubric.name
        rubric.weight = self._normalize_weight(weight)
        rubric.later_stage_only = bool(later_stage_only)
        db.add(rubric)
        self._validate_rubric_set(db, rubrics)
        db.commit()
        db.refresh(rubric)
        return rubric

    def delete_rubric(self, db: Session, rubric_id: int) -> dict:
        rubric = db.get(ScoringRubric, rubric_id)
        if not rubric:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found.")

        rubrics = self.list_rubrics(db)
        remaining = [item for item in rubrics if item.id != rubric_id]
        self._validate_rubric_set(db, remaining)
        db.delete(rubric)
        db.commit()
        return {"deleted_rubric_id": rubric_id, "message": "Rubric deleted successfully."}

    def normalize_scores(self, raw_scores: dict, rubrics: list[ScoringRubric]) -> dict[str, float]:
        normalized: dict[str, float] = {}
        for rubric in rubrics:
            normalized[rubric.key] = self.clamp_score(raw_scores.get(rubric.key))
        return normalized

    def clamp_score(self, value: object) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 1.0
        return round(max(1.0, min(10.0, numeric)), 2)

    def compute_weighted_total(self, score_map: dict[str, float], rubrics: list[ScoringRubric]) -> float:
        weighted_rubrics = [rubric for rubric in rubrics if rubric.weight > 0]
        total_weight = sum(float(rubric.weight) for rubric in weighted_rubrics)
        if total_weight <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The configured rubric weights sum to zero. Set at least one rubric to a positive weight.",
            )
        weighted_total = sum(float(score_map.get(rubric.key, 1.0)) * float(rubric.weight) for rubric in weighted_rubrics) / total_weight
        return round(weighted_total, 2)

    def build_weight_snapshot(self, rubrics: list[ScoringRubric]) -> list[dict]:
        positive_rubrics = [rubric for rubric in rubrics if rubric.weight > 0]
        total_weight = sum(float(rubric.weight) for rubric in positive_rubrics) or 1.0
        return [
            {
                "id": rubric.id,
                "key": rubric.key,
                "name": rubric.name,
                "weight": round(float(rubric.weight), 2),
                "normalized_weight": round(float(rubric.weight) / total_weight, 4),
                "later_stage_only": rubric.later_stage_only,
            }
            for rubric in positive_rubrics
        ]

    def build_legacy_compatibility_scores(self, score_map: dict[str, float], total_score: float) -> dict[str, float]:
        return {
            "innovation_score": round(float(score_map.get("innovation", total_score)), 2),
            "technical_score": round(float(score_map.get("technical_depth", total_score)), 2),
            "clarity_score": round(float(score_map.get("clarity", total_score)), 2),
            "impact_score": round(float(score_map.get("impact", total_score)), 2),
        }

    def ensure_seeded(self, db: Session) -> None:
        if list(db.scalars(select(ScoringRubric.id).limit(1))):
            return

        for payload in DEFAULT_RUBRICS:
            db.add(ScoringRubric(**payload))
        db.flush()
        self._validate_rubric_set(db, self.list_rubrics(db))

    def _normalize_weight(self, weight: float) -> float:
        try:
            numeric = float(weight)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rubric weight must be numeric.") from exc
        if numeric < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rubric weight cannot be negative.")
        return round(numeric, 2)

    def _validate_rubric_set(self, db: Session, rubrics: list[ScoringRubric]) -> None:
        if not rubrics:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="At least one scoring rubric is required.")

        later_stage_count = sum(1 for rubric in rubrics if rubric.later_stage_only)
        if later_stage_count > 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only one later-stage-only rubric is supported right now.",
            )

        base_total = round(sum(float(rubric.weight) for rubric in rubrics if not rubric.later_stage_only), 2)
        if base_total <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="At least one base rubric with positive weight is required so Stage 1 and legacy evaluations can be scored.",
            )

    def _build_unique_key(self, name: str, existing_keys: set[str]) -> str:
        base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "rubric"
        if base not in existing_keys:
            return base

        suffix = 2
        while f"{base}_{suffix}" in existing_keys:
            suffix += 1
        return f"{base}_{suffix}"


rubric_service = RubricService()
