from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.database import SessionLocal, init_db
from backend.routes.auth import router as auth_router
from backend.routes.continuous import router as continuous_router
from backend.routes.students import router as students_router
from backend.routes.submissions import router as submissions_router
from backend.routes.teacher import router as teacher_router
from backend.services.continuous_evaluation import continuous_evaluation_service
from backend.services.seed import seed_demo_data


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.ensure_directories()
    init_db()
    with SessionLocal() as db:
        seed_demo_data(db)
        continuous_evaluation_service.migrate_legacy_submissions(db)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(continuous_router)
app.include_router(submissions_router)
app.include_router(students_router)
app.include_router(teacher_router)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": settings.app_name}
