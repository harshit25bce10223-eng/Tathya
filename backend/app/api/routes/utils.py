from typing import Any
from fastapi import APIRouter, Depends
from pydantic.networks import EmailStr

from app.api.deps import get_current_active_superuser
from app.models import Message
from app.utils import generate_test_email, send_email

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=201,
)
def test_email(email_to: EmailStr) -> Message:
    """
    Test emails.
    """
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Test email sent")


@router.get("/health-check/")
async def health_check() -> bool:
    return True


@router.get("/models-status/", dependencies=[Depends(get_current_active_superuser)])
def get_models_status() -> dict[str, Any]:
    """Report configuration without inventing availability or latency measurements."""
    from app.core.config import settings
    from app.core.trust_score import SCORING_VERSION

    models = [
        {"name": settings.GEMINI_MODEL, "provider": "Google", "model_id": settings.GEMINI_MODEL,
         "role": "Verification fallback", "status": "CONFIGURED (availability unverified)" if settings.GEMINI_API_KEY else "UNCONFIGURED", "latency": "Not measured", "type": "Cloud LLM"},
        {"name": settings.OPENAI_MODEL, "provider": "OpenAI", "model_id": settings.OPENAI_MODEL,
         "role": "Verification fallback", "status": "CONFIGURED (availability unverified)" if settings.OPENAI_API_KEY else "UNCONFIGURED", "latency": "Not measured", "type": "Cloud LLM"},
        {"name": settings.EMBEDDING_MODEL, "provider": "Local", "model_id": settings.EMBEDDING_MODEL,
         "role": "Evidence retrieval", "status": "AVAILABILITY UNVERIFIED", "latency": "Not measured", "type": "Embedding model"},
        {"name": settings.RERANKER_MODEL, "provider": "Local", "model_id": settings.RERANKER_MODEL,
         "role": "Evidence reranking", "status": "AVAILABILITY UNVERIFIED", "latency": "Not measured", "type": "Reranker"},
        {"name": "Evidence-gated scoring", "provider": "Tathya", "model_id": SCORING_VERSION,
         "role": "Finding deductions and coverage", "status": "ACTIVE", "latency": "Not measured", "type": "Rules"},
    ]
    return {"active_primary_llm": None, "models": models,
            "total_active": 1, "availability_measured": False}
