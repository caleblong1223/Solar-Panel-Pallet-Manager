from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    business_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=100)
    is_active: bool = True
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=255)
    state: str | None = Field(default=None, max_length=64)
    zip_code: str | None = Field(default=None, max_length=32)


class CustomerUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    business_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=255)
    state: str | None = Field(default=None, max_length=64)
    zip_code: str | None = Field(default=None, max_length=32)


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    contact_name: str | None
    business_name: str | None
    email: EmailStr | None
    phone: str | None
    address: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    is_active: bool
    created_at: datetime

class CustomerListResponse(BaseModel):
    total: int
    customers: list[CustomerResponse]
