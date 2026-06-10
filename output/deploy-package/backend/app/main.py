from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import accounts, admin_reports, auth, employee_reports, processes, work_report_exports
from app.core.config import get_settings
from app.db.init_db import initialize_database
from app.db.session import get_db_session
from app.services.auth import get_current_user


def create_app() -> FastAPI:
    settings = get_settings()
    fastapi_kwargs: dict[str, object] = {"title": settings.app_name}
    if settings.is_production:
        fastapi_kwargs.update(docs_url=None, redoc_url=None, openapi_url=None)

    application = FastAPI(**fastapi_kwargs)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(auth.router)
    application.include_router(accounts.router)
    application.include_router(processes.router)
    application.include_router(employee_reports.router)
    application.include_router(admin_reports.router)
    application.include_router(work_report_exports.router)

    @application.on_event("startup")
    async def startup() -> None:
        await initialize_database()

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/db")
    async def database_health(
        request: Request,
        session: AsyncSession = Depends(get_db_session),
    ) -> dict[str, str | int]:
        if settings.is_production:
            try:
                current_user = await get_current_user(request, session)
            except HTTPException as exc:
                if exc.status_code == 401:
                    raise HTTPException(status_code=404, detail="not found") from None
                raise
            if current_user.get("role") not in {"super_admin", "admin"}:
                raise HTTPException(status_code=403, detail="forbidden")

        result = await session.execute(text("select 1"))
        return {"status": "ok", "database": result.scalar_one()}

    return application


app = create_app()
