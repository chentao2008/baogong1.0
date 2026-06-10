# Backend

后端目录，用于 FastAPI + SQLAlchemy ORM + PostgreSQL。

## 本地配置

复制环境变量示例文件：

```powershell
Copy-Item .env.example .env
```

然后修改 `.env` 中的 `DATABASE_URL`：

```text
postgresql+asyncpg://用户名:密码@localhost:5432/数据库名
```

## 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

## 验证数据库连接

```powershell
.\.venv\Scripts\python scripts\check_db.py
```

成功时会输出：

```text
database connected: 1
```

如果失败，优先检查：

- PostgreSQL 服务是否运行
- `.env` 中的用户名和密码是否正确
- `.env` 中的数据库名是否已经创建

## 启动开发服务

```powershell
.\.venv\Scripts\uvicorn app.main:app --reload
```

启动后可访问：

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/health/db`

开发前先阅读：

- `../docs/dev-agreement.md`
- `../docs/next-steps.md`
