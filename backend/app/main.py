from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import accounts, admin_reports, auth, employee_reports, processes, work_report_exports
from app.core.config import get_settings
from app.db.init_db import initialize_database
from app.db.session import get_db_session

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(processes.router)
app.include_router(employee_reports.router)
app.include_router(admin_reports.router)
app.include_router(work_report_exports.router)


@app.on_event("startup")
async def startup() -> None:
    await initialize_database()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/health/db")
async def database_health(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str | int]:
    result = await session.execute(text("select 1"))
    return {"status": "ok", "database": result.scalar_one()}
