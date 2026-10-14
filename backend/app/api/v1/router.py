from fastapi import APIRouter

from app.api.v1.calculate import router as calculate_router
from app.api.v1.chat import router as chat_router
from app.api.v1.checklists import router as checklists_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.notice import router as notice_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(feedback_router)
router.include_router(calculate_router)
router.include_router(notice_router)
router.include_router(checklists_router)
