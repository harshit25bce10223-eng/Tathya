from fastapi import APIRouter

from app.api.routes import audits, challenges, items, login, private, rope, users, utils, policies
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(audits.router)
api_router.include_router(audits.verify_router)
api_router.include_router(policies.router)
api_router.include_router(rope.router)
api_router.include_router(challenges.challenges_router)
api_router.include_router(challenges.inject_router)
api_router.include_router(challenges.judge_router)
api_router.include_router(challenges.proof_router)
api_router.include_router(challenges.metrics_router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
