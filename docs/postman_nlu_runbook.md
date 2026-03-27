# Postman 打通 NLU 解析链路

## 一次性调整

1. 先启动依赖和服务，至少需要 `postgres`、`redis`、`user-service`、`ai-service`、`gateway`。
2. 如果你的数据库已经跑过旧版 `user_service`，先执行认证字段迁移：

```powershell
psql -h localhost -U postgres -d highermatch_dev -f scripts/migrate_user_auth.sql
```

3. 当前实现要求 `user-service` 和 `ai-service` 共享同一组 JWT 配置。
   `.env` 里已经有 `JWT_SECRET_KEY` 和 `JWT_ALGORITHM`，两个服务都会读取这一组值。

## 推荐调用地址

- 走网关：`http://localhost/api/v1/...`
- 直连 user-service：`http://localhost:8001/api/v1/auth/...`
- 直连 ai-service：`http://localhost:8004/api/v1/nlu/parse`

## Postman 流程

### 1. 注册一个测试账号

- Method: `POST`
- URL: `http://localhost/api/v1/auth/register`
- Header: `Content-Type: application/json`
- Body:

```json
{
  "role": "candidate",
  "email": "nlu-demo@example.com",
  "phone": "13800138000",
  "password": "Demo1234",
  "name": "NLU Demo"
}
```

成功时会返回：

```json
{
  "success": true,
  "data": {
    "user_id": "1",
    "role": "candidate",
    "token": {
      "access_token": "...",
      "refresh_token": "...",
      "token_type": "bearer",
      "expires_in": 1800
    }
  }
}
```

### 2. 登录拿 access token

- Method: `POST`
- URL: `http://localhost/api/v1/auth/login`
- Header: `Content-Type: application/json`
- Body:

```json
{
  "email": "nlu-demo@example.com",
  "password": "Demo1234"
}
```

从返回体里取 `data.access_token`，后面放进 Bearer Token。

### 3. 调 NLU 解析接口

- Method: `POST`
- URL: `http://localhost/api/v1/nlu/parse`
- Header:
  - `Content-Type: application/json`
  - `Authorization: Bearer <data.access_token>`
- Body:

```json
{
  "text": "3年Python工程师，成都"
}
```

预期返回结构：

```json
{
  "success": true,
  "data": {
    "job_requirement_draft": {
      "job_title": "Python工程师",
      "skills": ["Python"],
      "years_exp_min": 3,
      "years_exp_max": 3,
      "location": ["成都"],
      "salary_min": null,
      "salary_max": null,
      "industry": null
    },
    "confidence_scores": {
      "job_title": 0.0,
      "skills": 0.0,
      "years_exp": 0.0,
      "location": 0.0,
      "salary": 0.0,
      "industry": 0.0
    },
    "clarification_questions": []
  },
  "cached": false,
  "processing_time_ms": 1234
}
```

## 常见失败点

- `401 AUTH_2000`：没有带 Bearer token。
- `401 AUTH_2001`：token 和 `JWT_SECRET_KEY` 不一致，或者 token 已过期。
- `422 NLU_1002`：LLM 调用失败，通常是 `LLM_API_KEY`、`LLM_API_BASE` 或外网访问有问题。

## 10 条样本准确率记录

- 样本文件：`scripts/nlu_eval_samples.json`
- 自动评测脚本：`scripts/nlu_accuracy_eval.py`
- tracking 表：`docs/nlu_accuracy_tracking.md`

执行方式：

```powershell
python scripts/nlu_accuracy_eval.py --base-url http://localhost --token "<access_token>"
```

执行后会生成 `docs/nlu_accuracy_tracking.csv`，方便直接发群或继续整理截图。
