import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import engine


async def main() -> None:
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("select 1"))
            print(f"database connected: {result.scalar_one()}")
    except Exception as exc:
        print("database connection failed")
        print("please check backend/.env DATABASE_URL")
        print(f"error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    asyncio.run(main())
