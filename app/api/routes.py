from fastapi import APIRouter
from .content_source_routes import router as content_source_router
from .auth_routes import router as auth_router
from .ai_plugin_routes import router as ai_plugin_router


router = APIRouter()


router.include_router(content_source_router)
router.include_router(auth_router)
router.include_router(ai_plugin_router)
