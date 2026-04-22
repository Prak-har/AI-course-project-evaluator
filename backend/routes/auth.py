from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import LoginRequest, LoginResponse
from backend.services.auth import login_user


router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = login_user(db, payload)
    return LoginResponse(role=payload.role, id=user.id, name=user.name, email=user.email)

