from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.files import router as files_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.core.config import get_settings
from app.db.session import engine


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version="0.1.0",
    )

    app.state.engine = engine
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(files_router, prefix=settings.api_prefix)
    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(jobs_router, prefix=settings.api_prefix)

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {
            "message": f"Welcome to {settings.app_name}",
            "environment": settings.app_env,
        }

    return app


app = create_app()
