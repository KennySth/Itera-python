from fastapi import APIRouter
from .endpoints import router as ia_router

router = APIRouter()
router.include_router(ia_router, prefix="/ia")
