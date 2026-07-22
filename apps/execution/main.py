from fastapi import FastAPI, BackgroundTasks
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from pydantic import BaseModel
from typing import Any

from apps.execution.database.models import Base
from apps.execution.translator import process_translation

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
async def startup_event() -> None:
    """Initialize database schemas on application startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Provide a basic health check endpoint for the execution engine.

    Returns:
        dict[str, str]: A dictionary containing the service status.
    """
    return {"status": "ok", "service": "execution"}

class StudyEvent(BaseModel):
    """Pydantic model representing an incoming study publication event.

    Attributes:
        study_id (str): The unique identifier of the study.
        payload (dict[str, Any]): The raw USDM protocol payload.
    """
    study_id: str
    payload: dict[str, Any]

@app.post("/events/study-published")
async def study_published(event: StudyEvent, background_tasks: BackgroundTasks) -> dict[str, str]:
    """Ingest study publication events and trigger layout generation asynchronously.

    Args:
        event (StudyEvent): The incoming study event payload.
        background_tasks (BackgroundTasks): FastAPI background task manager.

    Returns:
        dict[str, str]: A status message confirming job acceptance.
    """
    # Requirement 1: Listen for study publication events and trigger translation processes in the background.
    background_tasks.add_task(process_translation, event.study_id, event.payload, AsyncSessionLocal)
    return {"status": "accepted", "message": "Translation job queued in background."}
