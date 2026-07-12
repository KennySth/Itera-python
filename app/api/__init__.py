from fastapi import APIRouter
from .endpoints import router as ia_router

router = APIRouter(prefix="/api/ia")
router.include_router(ia_router)
