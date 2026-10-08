from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import TokenPayload, User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


# ---------------------------------------------------------------------------
# RBAC roles: user | reviewer | admin  (base-template auth, no SSO)
# ---------------------------------------------------------------------------

ROLE_ORDER = ("user", "reviewer", "admin")


def role_at_least(role: str, required: str) -> bool:
    if role == "admin":
        return True
    return role == required


def require_roles(*allowed: str):
    """FastAPI dependency factory: user must hold one of the given roles.

    admin implicitly satisfies every requirement; superuser bypasses checks.
    """

    def dependency(current_user: CurrentUser) -> User:
        if current_user.is_superuser:
            return current_user
        if current_user.role == "admin" or current_user.role in allowed:
            return current_user
        raise HTTPException(
            status_code=403,
            detail=f"Requires one of roles: {', '.join(allowed)}",
        )

    return dependency


ReviewerDep = Annotated[User, Depends(require_roles("reviewer", "admin"))]
AdminDep = Annotated[User, Depends(require_roles("admin"))]
