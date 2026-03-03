from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_pallets() -> dict[str, str]:
    return {"message": "TODO: list pallets"}


@router.post("")
def create_pallet() -> dict[str, str]:
    return {"message": "TODO: create pallet"}
