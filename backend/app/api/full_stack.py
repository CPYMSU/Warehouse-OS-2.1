from fastapi import APIRouter

from app.api.full_stack_business import router as business_router
from app.api.full_stack_identity import router as identity_router

router = APIRouter()
router.include_router(identity_router)
router.include_router(business_router)
