from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    role: Literal["student", "teacher"]
    email: EmailStr
    name: str | None = None
    password: str | None = None


class LoginResponse(BaseModel):
    role: Literal["student", "teacher"]
    id: int
    name: str
    email: EmailStr


class UploadResponse(BaseModel):
    submission_id: int
    title: str
    file_type: str
    embedded: bool
    warning: str | None = None
    created_at: datetime


class EvaluateRequest(BaseModel):
    submission_id: int
    draft: bool = True


class StageUpdateRequest(BaseModel):
    name: str
    max_marks: float


class StageCreateRequest(BaseModel):
    name: str
    max_marks: float


class StageEvaluateRequest(BaseModel):
    stage_submission_id: int


class StageUploadResponse(BaseModel):
    stage_submission_id: int
    project_id: int
    stage_id: int
    embedded: bool
    warning: str | None = None
    created_at: datetime


class RubricBaseRequest(BaseModel):
    name: str
    weight: float
    later_stage_only: bool = False


class RubricCreateRequest(RubricBaseRequest):
    pass


class RubricUpdateRequest(RubricBaseRequest):
    pass


class StudentBase(BaseModel):
    id: int
    name: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class GradeBase(BaseModel):
    id: int
    final_score: float
    grade: str
    z_score: float
    rank: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
