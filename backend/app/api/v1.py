"""Single place where every module's router is plugged into the app."""
from fastapi import APIRouter, Depends

from app.core.permissions import maintenance_guard
from app.modules.admin.router import router as admin_router
from app.modules.analytics.router import router as analytics_router
from app.modules.companies.router import router as companies_router
from app.modules.feed.router import router as feed_router
from app.modules.identity.router import router as identity_router
from app.modules.media.router import router as media_router
from app.modules.messaging.router import router as messaging_router
from app.modules.network.router import router as network_router
from app.modules.notifications.router import router as notifications_router
from app.modules.opportunities.router import router as opportunities_router
from app.modules.platform.router import router as platform_router
from app.modules.profiles.router import router as profiles_router
from app.modules.search.router import router as search_router
from app.modules.stories.router import router as stories_router

# Only staff get through these while maintenance mode is on. Identity (login handles it itself),
# platform (bootstrap must always answer) and media (images must keep loading) are exempt.
_guarded = [Depends(maintenance_guard)]

api_router = APIRouter()
api_router.include_router(platform_router)
api_router.include_router(identity_router)
api_router.include_router(media_router)
api_router.include_router(profiles_router, dependencies=_guarded)
api_router.include_router(network_router, dependencies=_guarded)
api_router.include_router(companies_router, dependencies=_guarded)
api_router.include_router(opportunities_router, dependencies=_guarded)
api_router.include_router(feed_router, dependencies=_guarded)
api_router.include_router(stories_router, dependencies=_guarded)
api_router.include_router(messaging_router, dependencies=_guarded)
api_router.include_router(notifications_router, dependencies=_guarded)
api_router.include_router(search_router, dependencies=_guarded)
api_router.include_router(admin_router, dependencies=_guarded)
api_router.include_router(analytics_router, dependencies=_guarded)
