from fastapi import APIRouter

from .login import router as login_router
from .logout import router as logout_router
from .posts import router as posts_router
from .rate_limits import router as rate_limits_router
from .tiers import router as tiers_router
from .users import router as users_router
from .content_generation import router as content_generation_router
from .project import router as project_router
from .social_auth import router as social_auth_router
from .scheduled_tasks import router as scheduled_tasks_router
from .analytics import router as analytics_router

router = APIRouter(prefix="/v1")
router.include_router(login_router)
router.include_router(logout_router)
router.include_router(users_router)
router.include_router(posts_router)
router.include_router(tiers_router)
router.include_router(rate_limits_router)
router.include_router(content_generation_router)
router.include_router(project_router)
router.include_router(social_auth_router, prefix="/social_auth")
router.include_router(scheduled_tasks_router, prefix="/tasks")
router.include_router(analytics_router, prefix="/analytics")
