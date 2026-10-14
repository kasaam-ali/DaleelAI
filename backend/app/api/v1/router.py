from fastapi import APIRouter

from app.api.v1.calculate import router as calculate_router
from app.api.v1.chat import router as chat_router
from app.api.v1.feedback import router as feedback_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(feedback_router)
router.include_router(calculate_router)
