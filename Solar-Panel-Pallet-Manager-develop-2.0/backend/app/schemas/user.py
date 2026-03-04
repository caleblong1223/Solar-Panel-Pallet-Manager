from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserPublic(UserBase):
    pass

