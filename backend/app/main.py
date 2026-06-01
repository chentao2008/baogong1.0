import json
import time
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROCESS_DATA_FILE = DATA_DIR / "processes.json"
DEFAULT_PROCESSES = [
    {"id": "p-cut", "name": "裁剪", "price": 1.2, "unit": "元/米", "status": "active"},
    {"id": "p-sew", "name": "缝制", "price": 2.6, "unit": "元/条", "status": "active"},
    {"id": "p-pack", "name": "包装", "price": 0.8, "unit": "元/包", "status": "disabled"},
]


class ProcessCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    unit: str = Field(min_length=1)


class ProcessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1)
    status: Literal["active", "disabled"] | None = None


def read_processes() -> list[dict[str, str | float]]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROCESS_DATA_FILE.exists():
        write_processes(DEFAULT_PROCESSES)
        return [process.copy() for process in DEFAULT_PROCESSES]

    try:
        data = json.loads(PROCESS_DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = DEFAULT_PROCESSES
        write_processes(data)

    if not isinstance(data, list):
        data = DEFAULT_PROCESSES
        write_processes(data)

    return data


def write_processes(processes: list[dict[str, str | float]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESS_DATA_FILE.write_text(
        json.dumps(processes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def find_process(processes: list[dict[str, str | float]], process_id: str) -> dict[str, str | float]:
    for process in processes:
        if process.get("id") == process_id:
            return process
    raise HTTPException(status_code=404, detail="process not found")


def ensure_unique_name(processes: list[dict[str, str | float]], name: str, process_id: str | None = None) -> None:
    if any(process.get("name") == name and process.get("id") != process_id for process in processes):
        raise HTTPException(status_code=409, detail="process name already exists")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/health/db")
async def database_health(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str | int]:
    result = await session.execute(text("select 1"))
    return {"status": "ok", "database": result.scalar_one()}


@app.get("/api/admin/processes")
async def list_processes() -> list[dict[str, str | float]]:
    return read_processes()


@app.post("/api/admin/processes", status_code=201)
async def create_process(payload: ProcessCreate) -> dict[str, str | float]:
    processes = read_processes()
    name = payload.name.strip()
    unit = payload.unit.strip()
    ensure_unique_name(processes, name)

    process = {
        "id": f"p-{int(time.time() * 1000)}",
        "name": name,
        "price": payload.price,
        "unit": unit,
        "status": "active",
    }
    processes.append(process)
    write_processes(processes)
    return process


@app.patch("/api/admin/processes/{process_id}")
async def update_process(process_id: str, payload: ProcessUpdate) -> dict[str, str | float]:
    processes = read_processes()
    process = find_process(processes, process_id)

    if payload.name is not None:
        name = payload.name.strip()
        ensure_unique_name(processes, name, process_id)
        process["name"] = name
    if payload.price is not None:
        process["price"] = payload.price
    if payload.unit is not None:
        process["unit"] = payload.unit.strip()
    if payload.status is not None:
        process["status"] = payload.status

    write_processes(processes)
    return process


@app.delete("/api/admin/processes/{process_id}", status_code=204)
async def delete_process(process_id: str) -> None:
    processes = read_processes()
    next_processes = [process for process in processes if process.get("id") != process_id]
    if len(next_processes) == len(processes):
        raise HTTPException(status_code=404, detail="process not found")

    write_processes(next_processes)
