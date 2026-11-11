
from typing import Annotated, Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import TOKEN_EXPIRED, decode_access_token_with_reason
from app.core.logger import bind_context
from app.modules.audit.audit_service import EVENT_TOKEN_INVALID, RESULT_FAILED, record_audit
from app.modules.auth.auth_model import User, Role

security = HTTPBearer()


def _reject_token(reason: str, username: Optional[str] = None, detail: str = "Could not validate credentials"):
    # Expired tokens are the normal refresh flow, not a security event
    if reason != TOKEN_EXPIRED:
        record_audit(EVENT_TOKEN_INVALID, RESULT_FAILED, username=username, failure_reason=reason)
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    token = credentials.credentials
    
    payload, reason = decode_access_token_with_reason(token)
    if payload is None:
        raise _reject_token(reason)
    
    username: str = payload.get("sub")
    if username is None:
        raise _reject_token("MISSING_SUBJECT")
    
    user = (
        db.query(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.warehouses),
        )
        .filter(User.username == username)
        .first()
    )
    if user is None:
        raise _reject_token("USER_NOT_FOUND", username=username, detail="User not found")

    bind_context(user=user.username, user_id=user.id)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return user


def require_role(*allowed_roles: str) -> Callable:
    def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        user_role_names = {role.name for role in current_user.roles}
        if not user_role_names.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return current_user
    return role_checker

def require_permission(*codes: str) -> Callable:
    def checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if any(role.name == "admin" for role in current_user.roles):
            return current_user
        user_codes = {
            p.code
            for role in current_user.roles
            for p in role.permissions
        }
        # Admin wildcard via role_permissions
        if "*" in user_codes:
            return current_user
        if not set(codes).issubset(user_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return checker


def get_dev_admin_user(
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Temporary integration bypass: no Bearer token; always use active admin user."""
    user = (
        db.query(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.warehouses),
        )
        .filter(User.username == "admin", User.is_active.is_(True))
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dev admin user not found (expected username 'admin')",
        )
    bind_context(user=user.username, user_id=user.id)
    return user
