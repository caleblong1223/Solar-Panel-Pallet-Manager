from fastapi import APIRouter

from app.api.v1.endpoints import auth, barcodes, customers, exports, health, pallets, simulator

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(pallets.router, prefix="/pallets", tags=["pallets"])
api_router.include_router(barcodes.router, prefix="/barcodes", tags=["barcodes"])
api_router.include_router(simulator.router, prefix="/simulator", tags=["simulator"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
