from fastapi import APIRouter

router = APIRouter()


@router.get("/search")
def search_barcodes() -> dict[str, str]:
    return {"message": "TODO: search barcodes"}
