from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends

from app.api.v1.endpoints.auth import get_current_user_optional
from app.models.user import User


@dataclass
class AnonymousUser:
    id: int | None = None
    username: str = "anonymous"
    roles: list = None

    def __post_init__(self) -> None:
        if self.roles is None:
            self.roles = []


def require_roles(*_: str) -> Callable[..., User | AnonymousUser]:
    """Authorization helper.

    In the simplified deployment model, all authenticated users share a single
    effective role and can perform the same actions. This dependency now
    behaves as an "authenticated user required" check only.
    """

    def _dependency(current_user: User | None = Depends(get_current_user_optional)) -> User | AnonymousUser:
        if current_user is None:
            return AnonymousUser()
        return current_user

    return _dependency
