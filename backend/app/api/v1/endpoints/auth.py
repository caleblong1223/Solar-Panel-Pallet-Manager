from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
def login() -> dict[str, str]:
    return {"message": "TODO: implement login"}


@router.get("/me")
def me() -> dict[str, str]:
    return {"message": "TODO: implement current user"}
