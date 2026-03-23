from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.auth import router as auth_router
from src.api.routers.analytics import router as analytics_router
from src.api.routers.babies import router as babies_router
from src.api.routers.notifications import router as notifications_router
from src.api.routers.parents import router as parents_router
from src.api.routers.screening import router as screening_router
from src.api.routers.users import router as users_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="РНС Якутия API",
        description="API системы расширенного неонатального скрининга РС(Я)",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(auth_router)
    app.include_router(screening_router)
    app.include_router(parents_router)
    app.include_router(babies_router)
    app.include_router(notifications_router)
    app.include_router(analytics_router)
    app.include_router(users_router)

    # Admin panel
    from src.admin.router import router as admin_router

    app.include_router(admin_router)

    # Parent portal
    from src.portal.router import router as portal_router

    app.include_router(portal_router)

    # Static files
    import os

    static_dir = os.path.join(os.path.dirname(__file__), "..", "admin", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    return app
