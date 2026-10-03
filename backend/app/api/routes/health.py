"""Health / readiness probe."""

from fastapi import APIRouter

from app.agent.memory import VectorRecall
from app.core.config import settings

router = APIRouter(tags=["health"])
_recall = VectorRecall()


@router.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_base_url": settings.llm_base_url,
        "llm_model": settings.llm_model,
        "vector_recall": _recall.healthy,
    }
