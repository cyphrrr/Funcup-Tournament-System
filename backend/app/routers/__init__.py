from fastapi import APIRouter
from .auth import router as auth_router
from .seasons import router as seasons_router
from .teams import router as teams_router
from .matches import router as matches_router
from .ko import router as ko_router
from .news import router as news_router
from .users import router as users_router
from .admin import router as admin_router
from .oauth import router as oauth_router
from .uploads import router as uploads_router
from ..services.standings import router as standings_router

router = APIRouter()

# Auth zuerst
router.include_router(auth_router)
# Teams: /teams/search MUSS vor /teams/{team_id} registriert werden
router.include_router(teams_router)
# Restliche Router
router.include_router(seasons_router)
router.include_router(matches_router)
router.include_router(ko_router)
router.include_router(news_router)
router.include_router(users_router)
router.include_router(admin_router)
router.include_router(oauth_router)
router.include_router(uploads_router)
router.include_router(standings_router)
