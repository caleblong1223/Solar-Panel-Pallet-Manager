from pydantic import BaseModel

from app.schemas.user import UserPublic


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class MeResponse(UserPublic):
    pass

