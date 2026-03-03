from fastapi import APIRouter

router = APIRouter()


@router.post("")
def create_export() -> dict[str, str]:
    return {"message": "TODO: create export"}
