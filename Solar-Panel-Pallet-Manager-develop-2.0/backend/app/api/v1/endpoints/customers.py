from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.pallet import Customer
from app.schemas.customer import CustomerCreate, CustomerListResponse, CustomerResponse, CustomerUpdate

router = APIRouter()


@router.get("", response_model=CustomerListResponse)
def list_customers(
    search: str | None = None,
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> CustomerListResponse:
    query = db.query(Customer)
    if search:
        query = query.filter(Customer.display_name.ilike(f"%{search.strip()}%"))
    if is_active is not None:
        query = query.filter(Customer.is_active == is_active)
    total = query.count()
    customers = query.order_by(Customer.display_name.asc()).offset(offset).limit(limit).all()
    return CustomerListResponse(total=total, customers=[CustomerResponse.model_validate(c) for c in customers])


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
) -> CustomerResponse:
    existing = db.query(Customer.id).filter(Customer.display_name == payload.display_name.strip()).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Customer display_name already exists")
    customer = Customer(
        display_name=payload.display_name.strip(),
        contact_name=payload.contact_name,
        business_name=payload.business_name,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        zip_code=payload.zip_code,
        is_active=payload.is_active,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
) -> CustomerResponse:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return CustomerResponse.model_validate(customer)


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
) -> CustomerResponse:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    if payload.display_name is not None:
        normalized_name = payload.display_name.strip()
        existing = (
            db.query(Customer.id)
            .filter(Customer.display_name == normalized_name, Customer.id != customer_id)
            .first()
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Customer display_name already exists",
            )
        customer.display_name = normalized_name
    if payload.contact_name is not None:
        customer.contact_name = payload.contact_name
    if payload.business_name is not None:
        customer.business_name = payload.business_name
    if payload.email is not None:
        customer.email = str(payload.email)
    if payload.phone is not None:
        customer.phone = payload.phone
    if payload.is_active is not None:
        customer.is_active = payload.is_active
    if payload.address is not None:
        customer.address = payload.address
    if payload.city is not None:
        customer.city = payload.city
    if payload.state is not None:
        customer.state = payload.state
    if payload.zip_code is not None:
        customer.zip_code = payload.zip_code

    db.commit()
    db.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
) -> None:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    customer.is_active = False
    db.commit()
