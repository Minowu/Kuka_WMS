
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.logger import bind_context
from app.modules.auth.auth_model import User, Role

security = HTTPBearer()

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    token = credentials.credentials
    
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    bind_context(user=user.username)
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
    bind_context(user=user.username)
    return user
