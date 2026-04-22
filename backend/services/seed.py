from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import StageDefinition, Student, Teacher
from backend.services.rubrics import rubric_service


settings = get_settings()

DEMO_STUDENTS = [
    {"name": "Aarav Sharma", "email": "aarav@example.com"},
    {"name": "Ishita Verma", "email": "ishita@example.com"},
    {"name": "Neel Rao", "email": "neel@example.com"},
    {"name": "Riya Sen", "email": "riya@example.com"},
]

DEFAULT_STAGES = [
    {"name": "Stage 1", "stage_order": 1, "max_marks": 10.0},
    {"name": "Stage 2", "stage_order": 2, "max_marks": 10.0},
    {"name": "Stage 3", "stage_order": 3, "max_marks": 10.0},
]


def seed_demo_data(db: Session) -> None:
    teacher = db.scalar(select(Teacher).where(Teacher.email == settings.demo_teacher_email))
    if not teacher:
        db.add(
            Teacher(
                name=settings.demo_teacher_name,
                email=settings.demo_teacher_email,
                password=settings.demo_teacher_password,
            )
        )

    if not list(db.scalars(select(StageDefinition).order_by(StageDefinition.stage_order))):
        for payload in DEFAULT_STAGES:
            db.add(StageDefinition(**payload))

    rubric_service.ensure_seeded(db)

    if settings.auto_seed_demo_students:
        existing_student_count = db.scalar(select(func.count(Student.id))) or 0
        if existing_student_count:
            db.commit()
            return

        for student_payload in DEMO_STUDENTS:
            existing = db.scalar(select(Student).where(Student.email == student_payload["email"]))
            if not existing:
                db.add(Student(**student_payload))

    db.commit()
