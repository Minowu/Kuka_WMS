"""Central role name constants — no hardcoded role strings in APIs/services."""

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"

KNOWN_ROLES = frozenset({ROLE_ADMIN, ROLE_OPERATOR})


def user_has_role(user, role_name: str) -> bool:
    return bool(any(r.name == role_name for r in (getattr(user, "roles", None) or [])))


def user_is_admin(user) -> bool:
    return user_has_role(user, ROLE_ADMIN)
