from fastapi import FastAPI, BackgroundTasks
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from pydantic import BaseModel
import contextvars

from apps.execution.database.models import Base
from apps.execution.translator import process_translation
from apps.execution.database.context import current_session

app = FastAPI(title="Cadence Clinical - EDC Execution Engine", version="0.1.0")

# Setup an in-memory SQLite DB for testing
engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "execution"}

class StudyEvent(BaseModel):
    study_id: str
    payload: dict

@app.post("/events/study-published")
async def study_published(event: StudyEvent, background_tasks: BackgroundTasks):
    # Requirement 1: Listen for study publication events and trigger translation processes in the background.
    background_tasks.add_task(process_translation, event.study_id, event.payload, AsyncSessionLocal)
    return {"status": "accepted", "message": "Translation job queued in background."}
