from collections.abc import Callable

from fastapi import Depends

from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User


def require_roles(*_: str) -> Callable[..., User]:
    """Authorization helper.

    In the simplified deployment model, all authenticated users share a single
    effective role and can perform the same actions. This dependency now
    behaves as an "authenticated user required" check only.
    """

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        return current_user

    return _dependency
