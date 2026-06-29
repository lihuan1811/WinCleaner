# WinCleaner FastAPI Backend

本后端用于账户、登录、会员卡兑换和后续增值服务授权，数据库使用 PostgreSQL。

## 本地启动

```bash
docker compose up -d postgres
python -m pip install -r requirements.txt
uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

默认连接：

```text
postgresql://wincleaner:wincleaner@127.0.0.1:5432/wincleaner
```

生产环境或阿里云 RDS PostgreSQL 只需要配置：

```bash
DATABASE_URL=postgresql://user:password@host:5432/database
```

## API

- `GET /health`
- `GET /api/account/state/{device_id}`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/cards/redeem`

启动后可打开：

```text
http://127.0.0.1:8000/docs
```

## 默认测试卡密

- `WINCLEANER-VIP-30D`
- `WINCLEANER-VIP-365D`
- `WINCLEANER-TEAM-365D`

## 运行 PostgreSQL 集成测试

集成测试会清空测试库表，测试数据库名必须以 `_test` 结尾。

```bash
docker compose up -d postgres
docker compose exec postgres createdb -U wincleaner wincleaner_test
TEST_DATABASE_URL=postgresql://wincleaner:wincleaner@127.0.0.1:5432/wincleaner_test \
  pytest tests/test_backend_account_api.py
```
