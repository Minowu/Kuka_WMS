"""Authentication service."""

from datetime import timedelta
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_password_hash,
    verify_password,
)
from app.modules.auth.auth_access import build_user_access_summary, user_to_response
from app.modules.auth.auth_model import User, Role, Permission, UserRole, UserWarehouse
from app.modules.auth.auth_schema import (
    LoginRequest,
    LoginResponse,
    TokenResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserSignupResponse,
    UserUpdate,
    StaffUsernamesResponse,
)
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse


def _user_query(db: Session, *, include_inactive: bool = False):
    return db.query(User).options(
        selectinload(User.roles).selectinload(Role.permissions),
        selectinload(User.warehouses),
    )


def _get_active_user_by_username(db: Session, username: str) -> Optional[User]:
    return _user_query(db).filter(User.username == username).first()


def _get_active_user_by_email(
    db: Session,
    email: str,
    *,
    exclude_user_id: Optional[int] = None,
) -> Optional[User]:
    q = _user_query(db).filter(User.email == email)
    if exclude_user_id is not None:
        q = q.filter(User.id != exclude_user_id)
    return q.first()


def _get_roles_by_ids(db: Session, role_ids: list[int]) -> list[Role]:
    if not role_ids:
        return []
    roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
    missing = set(role_ids) - {r.id for r in roles}
    if missing:
        raise ValueError(f"Role ids not found: {sorted(missing)}")
    return roles


def _get_roles_by_names(db: Session, names: list[str]) -> list[Role]:
    if not names:
        return []
    roles = db.query(Role).filter(Role.name.in_(names)).all()
    found = {r.name for r in roles}
    missing = set(names) - found
    if missing:
        raise ValueError(f"Role names not found: {sorted(missing)}")
    # Preserve requested order
    by_name = {r.name: r for r in roles}
    return [by_name[n] for n in names]


def _get_warehouses_by_ids(db: Session, warehouse_ids: list[int]) -> list[Warehouse]:
    if not warehouse_ids:
        return []
    warehouses = db.query(Warehouse).filter(Warehouse.id.in_(warehouse_ids)).all()
    missing = set(warehouse_ids) - {w.id for w in warehouses}
    if missing:
        raise ValueError(f"Warehouse ids not found: {sorted(missing)}")
    by_id = {w.id: w for w in warehouses}
    return [by_id[i] for i in warehouse_ids]


def _is_admin_role_ids(db: Session, role_ids: list[int]) -> bool:
    if not role_ids:
        return False
    roles = _get_roles_by_ids(db, role_ids)
    return any(r.name == "admin" for r in roles)


def _ensure_admin_role_with_wildcard(db: Session) -> Role:
    """Ensure admin role exists and is linked to permission '*'."""
    admin_role = (
        db.query(Role)
        .options(selectinload(Role.permissions))
        .filter(Role.name == "admin")
        .first()
    )
    if not admin_role:
        raise ValueError("Admin role not found. Run seed_data.")
    wildcard = db.query(Permission).filter(Permission.code == "*").first()
    if not wildcard:
        raise ValueError("Wildcard permission '*' not found. Run seed_data.")
    if not any(p.code == "*" for p in admin_role.permissions):
        admin_role.permissions = [*admin_role.permissions, wildcard]
        db.flush()
    return admin_role


def _assign_admin_access(db: Session, user: User) -> None:
    admin_role = _ensure_admin_role_with_wildcard(db)
    user.roles = [admin_role]
    user.warehouses = []


def _is_admin_request(
    *,
    is_admin: Optional[bool],
    role_ids: Optional[list[int]],
    db: Session,
) -> bool:
    if is_admin is True:
        return True
    if is_admin is False:
        return False
    if role_ids:
        return _is_admin_role_ids(db, role_ids)
    return False


def _apply_access_on_create(db: Session, user: User, body: UserCreate) -> None:
    if _is_admin_request(is_admin=body.is_admin, role_ids=body.role_ids, db=db):
        _assign_admin_access(db, user)
        return
    if body.role_ids:
        user.roles = _get_roles_by_ids(db, body.role_ids)
    else:
        cnc_role = db.query(Role).filter(Role.name == "operator_cnc").first()
        user.roles = [cnc_role] if cnc_role else []
    user.warehouses = db.query(Warehouse).all()


def _apply_access_on_update(db: Session, user: User, body: UserUpdate) -> None:
    data = body.model_dump(exclude_unset=True)
    role_ids = data.get("role_ids")
    is_admin = data.get("is_admin")

    access_touched = "role_ids" in data or "is_admin" in data
    if not access_touched:
        return

    if _is_admin_request(is_admin=is_admin, role_ids=role_ids, db=db):
        _assign_admin_access(db, user)
        return

    if role_ids is not None:
        user.roles = _get_roles_by_ids(db, role_ids)


def login(db: Session, body: LoginRequest) -> LoginResponse:
    user = authenticate_user(db, body.username, body.password)
    if not user:
        raise ValueError("Invalid username or password")
    return LoginResponse(
        user=user_to_response(db, user),
        tokens=TokenResponse(
            access_token=create_access_token({"sub": user.username}),
            refresh_token=create_refresh_token({"sub": user.username}),
            token_type="bearer",
        ),
    )


def sign_up(db: Session, user_in: UserCreate) -> UserSignupResponse:
    if _get_active_user_by_username(db, user_in.username):
        raise ValueError("User with this username already exists")

    if _get_active_user_by_email(db, user_in.email):
        raise ValueError("User with this email already exists")

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
    )
    try:
        db.add(new_user)
        db.flush()
        _apply_access_on_create(db, new_user, user_in)
        if getattr(user_in, "location_ids", None):
            from app.modules.production.production_models import UserLocation
            for lid in user_in.location_ids:
                db.add(UserLocation(user_id=new_user.id, location_id=lid))
        db.commit()
        new_user = (
            _user_query(db, include_inactive=True)
            .filter(User.id == new_user.id)
            .one()
        )
    except ValueError:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {str(e.orig)}") from e

    tokens = TokenResponse(
        access_token=create_access_token({"sub": new_user.username}),
        refresh_token=create_refresh_token({"sub": new_user.username}),
        token_type="bearer",
    )

    return UserSignupResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        roles=new_user.roles,
        warehouses=new_user.warehouses,
        access=build_user_access_summary(db, new_user),
        is_active=new_user.is_active,
        tokens=tokens,
    )


def refresh_access_token(db: Session, refresh_token: str) -> Optional[str]:
    payload = decode_refresh_token(refresh_token)
    if not payload:
        return None

    username = payload.get("sub")
    if not username:
        return None

    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None

    return create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = _user_query(db).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def list_users(db: Session, page: int = 1, page_size: int = 20) -> UserListResponse:
    query = _user_query(db)
    total = query.count()
    users = (
        query.order_by(User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return UserListResponse(
        items=[user_to_response(db, u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


def list_staff_usernames(db: Session) -> StaffUsernamesResponse:
    """Active non-admin usernames (UI role 'Nhân viên')."""
    users = _user_query(db).order_by(User.username).all()
    usernames = [
        u.username
        for u in users
        if not any(r.name == "admin" for r in (u.roles or []))
    ]
    return StaffUsernamesResponse(usernames=usernames)


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return _user_query(db).filter(User.id == user_id).first()


def update_user(db: Session, user_id: int, body: UserUpdate) -> Optional[User]:
    user = (
        _user_query(db, include_inactive=True)
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        return None
    data = body.model_dump(exclude_unset=True)
    data.pop("password_confirm", None)
    if "email" in data:
        existing = _get_active_user_by_email(
            db, data["email"], exclude_user_id=user_id
        )
        if existing:
            raise ValueError("Email already in use")
        user.email = data["email"]
    if "password" in data:
        password = (data["password"] or "").strip()
        if password:
            user.hashed_password = get_password_hash(password)

    try:
        _apply_access_on_update(db, user, body)
        db.commit()
        user = _user_query(db, include_inactive=True).filter(User.id == user_id).one()
    except ValueError:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    from app.modules.production.production_models import (
        UserLocation,
        TransportRequest,
        ProductionRecord,
    )
    # 1. Nullify references in history records to preserve audit trail
    db.query(TransportRequest).filter(TransportRequest.created_by == user_id).update(
        {"created_by": None}, synchronize_session=False
    )
    db.query(ProductionRecord).filter(ProductionRecord.operator_id == user_id).update(
        {"operator_id": None}, synchronize_session=False
    )
    # 2. Delete external relationships
    db.query(UserLocation).filter(UserLocation.user_id == user_id).delete(synchronize_session=False)
    # 3. Hard delete user permanently from database
    db.delete(user)
    db.commit()
    return True
