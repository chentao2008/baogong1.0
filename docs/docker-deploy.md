# Docker 部署说明

## 第一次部署

1. 复制生产配置：

```bash
cp .env.production.example .env.production
```

2. 修改 `.env.production`：

- `POSTGRES_PASSWORD`
- `DATABASE_URL` 里的数据库密码
- `FRONTEND_ORIGINS`
- `PASSWORD_VIEW_SECRET`
- `INITIAL_ADMIN_ACCOUNT`
- `INITIAL_ADMIN_PASSWORD`

3. 启动：

```bash
docker compose --env-file .env.production up -d --build
# 如果服务器只有旧版命令，用：
docker-compose --env-file .env.production up -d --build
```

4. 创建第一个管理员：

```bash
docker compose --env-file .env.production run --rm backend python scripts/create_initial_admin.py
# 如果服务器只有旧版命令，用：
docker-compose --env-file .env.production run --rm backend python scripts/create_initial_admin.py
```

5. 访问：

```text
http://服务器IP
```

## 后续更新

```bash
docker compose --env-file .env.production up -d --build
# 如果服务器只有旧版命令，用：
docker-compose --env-file .env.production up -d --build
```

## 备份数据库

```bash
docker compose --env-file .env.production exec db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
# 如果服务器只有旧版命令，用：
docker-compose --env-file .env.production exec db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```
