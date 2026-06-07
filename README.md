# 学生水电充值管理系统 (label-3598)

## 🛠 技术栈
- Frontend: Vue 3 + Vite + Element Plus + Pinia + Vue Router + Zod
- Backend: Django 4.2 + Django REST Framework + Simple JWT + Service Layer
- Database: PostgreSQL 15（兼容 OpenGauss 协议与 SQL 语法）

## 🚀 启动指南 (How to Run)
1. 确保 Docker Desktop 已启动。
2. 在根目录执行：`docker compose up --build`
3. 等待容器启动完成（首次约 3-5 分钟）。

## 🔗 服务地址 (Services)
- Frontend: http://localhost:3598
- Backend Swagger: http://localhost:8598/api/docs/
- Backend API Base: http://localhost:8598/api/
- Database: localhost:5598 (user: czxt / pass: Czxt@3598)

## 🧪 测试账号
- Admin: admin_3598 / Admin@123456
- Student: student_3598 / Student@123456

## ✅ 功能清单
- 注册登录模块：学生/管理员角色注册、学号+手机号/邮箱注册、计算题验证码、记住我
- 密码重置模块：安全问题校验 + 邮箱验证码（演示发送）+ 新密码重置
- 用户管理模块：管理员用户检索、角色调整、启用/禁用控制
- 充值订单模块：学生提交充值订单、管理员审核通过/驳回、订单状态通知
- 余额管理模块：余额查询、钱包冻结/解冻、余额变动日志追溯
- 消费记录模块：消费记录查询筛选、分类统计、按日趋势可视化
- 公告通知模块：管理员发布公告并推送，用户通知列表/已读管理

## 🧩 架构说明
- 后端按 `API层(View) -> 序列化校验(Serializer) -> 业务层(Service)` 组织。
- 充值、消费、冻结/解冻均由 `LedgerService` 统一处理，并在事务中写入余额日志。
- 接口鉴权使用 JWT，管理员能力通过角色权限 `IsAdminRole` 控制。
- 前端采用单页分角色工作台：学生端（订单、统计、通知）与管理员端（审核、用户、公告）。

## 🔒 数据库与连接
- 默认使用本地容器数据库，支持一键启动。
- 题目给定远程 OpenGauss 参数：`103.117.136.18:35432 / czxt / schema czxt / 用户 czxt`。
- 可通过 `.env` 配置切换连接参数：`DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD/DB_SCHEMA/DB_SSLMODE`。
- 连接稳定性：实现数据库重试脚本、连接池参数（`CONN_MAX_AGE`）、统一异常处理。

## 🧪 测试
- 后端测试：`docker compose exec -T backend python manage.py test --keepdb`
- 覆盖场景：密码重置链路、充值订单审核入账、冻结账户拦截、公告推送。

## 📚 文档
- 部署文档：[docs/DEPLOYMENT.md](/Users/carry/Documents/_D/label/label-3598/docs/DEPLOYMENT.md)
- 使用文档：[docs/USER_GUIDE.md](/Users/carry/Documents/_D/label/label-3598/docs/USER_GUIDE.md)

## 📦 目录结构
```text
label-3598/
├── backend/
├── frontend/
├── docs/
├── docker-compose.yml
└── README.md
```
