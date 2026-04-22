from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Student, Teacher
from backend.schemas import LoginRequest


def login_user(db: Session, payload: LoginRequest) -> Student | Teacher:
    if payload.role == "student":
        student = db.scalar(select(Student).where(Student.email == payload.email))
        if student:
            if payload.name and payload.name != student.name:
                student.name = payload.name
                db.commit()
                db.refresh(student)
            return student

        student = Student(
            name=payload.name or payload.email.split("@")[0].replace(".", " ").title(),
            email=payload.email,
        )
        db.add(student)
        db.commit()
        db.refresh(student)
        return student

    teacher = db.scalar(select(Teacher).where(Teacher.email == payload.email))
    if not teacher or payload.password != teacher.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid teacher credentials.")
    return teacher

