from fastapi import APIRouter

router = APIRouter()


@router.post("/imports")
def import_simulator_data() -> dict[str, str]:
    return {"message": "TODO: import simulator data"}
