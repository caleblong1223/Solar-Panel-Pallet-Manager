from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User


def require_roles(*allowed_roles: str) -> Callable[..., User]:
    allowed = set(allowed_roles)

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if not allowed:
            return current_user
        user_roles = {role.name for role in current_user.roles}
        if user_roles & allowed:
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    return _dependency
