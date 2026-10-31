from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes import (
    assets,
    capabilities,
    characters,
    csp,
    jobs,
    projects,
    references,
    settings as settings_routes,
    shots,
    story,
    studio,
    visual_library,
    wardrobe,
)
from creator_studio.infrastructure.container import get_container
from creator_studio.infrastructure.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    get_container()  # warm init + DB

    app = FastAPI(title="SceneWeaver API", version="0.2.0-dev")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(projects.router)
    app.include_router(jobs.router)
    app.include_router(capabilities.router)
    app.include_router(settings_routes.router)
    app.include_router(characters.router)
    app.include_router(references.router)
    app.include_router(studio.router)
    app.include_router(story.router)
    app.include_router(wardrobe.router)
    app.include_router(visual_library.router)
    app.include_router(shots.router)
    app.include_router(assets.router)
    app.include_router(csp.router)

    # Test-only control plane — never registered outside e2e / live-test
    if settings.allows_test_control:
        from apps.api.routes import test_control

        app.include_router(test_control.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "sceneweaver-api",
            "environment": settings.environment,
        }

    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "apps.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()