from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.security import decode_access_token

# HTTPBearer (not OAuth2PasswordBearer) on purpose: /auth/login takes a JSON
# body, not an OAuth2 form-encoded grant, so the OAuth2 "password" flow that
# Swagger's Authorize dialog performs can never succeed against it (it always
# POSTs username/password as form data -> 422). HTTPBearer instead gives the
# docs UI a plain "paste your token" field, which matches how the frontend
# actually authenticates (a manually-attached `Authorization: Bearer <token>`
# header) and needs no round trip back to the login endpoint.
bearer_scheme = HTTPBearer(auto_error=False)


def _resolve_user(token: str | None, db: Session) -> User:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc
    user = db.query(User).filter(User.username == payload.get("sub")).first()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials if credentials else None
    return _resolve_user(token, db)


def get_current_user_ws(token: str | None, db: Session) -> User:
    """Same resolution used for WebSocket/query-token auth (stream tags can't set headers)."""
    return _resolve_user(token, db)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator role required")
    return user


def get_optional_query_token(token: str | None = Query(default=None)) -> str | None:
    return token