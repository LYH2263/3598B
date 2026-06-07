# 部署文档

## 1. 环境要求
- Docker Desktop 4.x+
- 推荐内存 >= 4GB

## 2. 一键启动
```bash
cd /Users/carry/Documents/_D/label/label-3598
docker compose up --build
```

## 3. 服务检查
- 前端：`http://localhost:3598`
- 后端文档：`http://localhost:8598/api/docs/`
- 数据库：`localhost:5598`

## 4. 环境变量
可在根目录 `.env` 覆盖：
- `DJANGO_SECRET_KEY`：Django 密钥
- `DJANGO_DEBUG`：调试模式
- `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD`：数据库连接
- `DB_SCHEMA`：数据库 schema
- `DB_SSLMODE`：SSL 策略（disable/prefer/require）

## 5. 切换远程 OpenGauss
将 `.env` 修改为：
- `DB_HOST=103.117.136.18`
- `DB_PORT=35432`
- `DB_NAME=czxt`
- `DB_USER=czxt`
- `DB_PASSWORD=Czxt@2356`
- `DB_SCHEMA=czxt`

然后重启：
```bash
docker compose up -d --build backend frontend
```

## 6. 常见问题
- 问：接口 401 未授权？
  答：请先登录并确保前端本地存储 token 未过期。
- 问：验证码总是错误？
  答：已使用文件缓存跨 worker 共享；如仍异常可重启后端容器。
- 问：数据库连不上？
  答：先 `docker compose ps` 查看 `db` 是否 healthy，再看 `docker compose logs backend`。
