---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 3045022071a90a3da65bcc6946d35c6e9f8dae82893df5f5b5e0dad5687969777c29865c022100b4e141cba0341ef1b495bf3798544082083b8a1ab58f2233c321c83a60857cbe
    ReservedCode2: 3044022019a368c8efa657aabe2f7c7dc995052910b23f6f5a052a5b54a80b697b40a538022078265c8467022d2c20ff81b0f0412f795ca69fb8ee3a3efd00185c95aaca22f3
---

# HigherMatch™ 联调排查标准 SOP

> 本文档提供常见问题的排查命令和解决步骤，帮助开发者快速定位和解决问题。

---

## 📋 目录

- [1. CORS 错误](#1-cors-错误)
- [2. JWT 401 Unauthorized](#2-jwt-401-unauthorized)
- [3. Kafka 消息未消费](#3-kafka-消息未消费)
- [4. Qdrant 检索返回空](#4-qdrant-检索返回空)

---

## 1. CORS 错误

### 问题描述

```
Access to fetch at 'http://localhost:8001/api/v1/users' from origin 'http://localhost:5173'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present
```

或

```
Response to preflight request doesn't pass access control check:
It does not have HTTP ok status
```

### 排查步骤

#### Step 1: 确认是哪个服务报错

```bash
# 查看浏览器控制台确定请求的目标服务
# 例如报错请求是: http://localhost:8001/api/v1/xxx

# 则问题在 user-service
docker compose logs user-service | grep -i cors
```

#### Step 2: 检查服务 CORS 配置

```bash
# 进入服务容器
docker compose exec user-service sh

# 检查环境变量
echo $CORS_ORIGINS

# 确认包含前端地址
# 应该包含: http://localhost:5173 或 http://localhost
```

#### Step 3: 验证 CORS 配置正确

```bash
# 测试 CORS 预检请求
curl -X OPTIONS \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization,Content-Type" \
  -v http://localhost:8001/api/v1/users 2>&1 | grep -i "access-control"

# 正确响应应该包含:
# Access-Control-Allow-Origin: http://localhost:5173
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
# Access-Control-Allow-Headers: Authorization, Content-Type
```

### 常见原因与解决方案

| 原因 | 解决方案 |
|------|---------|
| CORS_ORIGINS 不包含前端地址 | 在 `.env` 中添加: `CORS_ORIGINS=http://localhost:5173,http://localhost` |
| CORS 配置格式错误 | 使用逗号分隔，不带引号 |
| Nginx 配置问题 | 检查 `nginx/conf.d/default.conf` 是否有代理添加 CORS 头 |
| 认证中间件拦截 OPTIONS | 确保认证中间件对 OPTIONS 请求放行 |

### 快速修复

```bash
# 方案1: 修改 .env
echo "CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost" >> .env

# 方案2: 直接在服务中添加 (临时)
docker compose exec user-service sh -c "echo 'CORS_ORIGINS=http://localhost:5173,http://localhost' >> /app/.env"

# 重启服务
docker compose restart user-service
```

---

## 2. JWT 401 Unauthorized

### 问题描述

```
{"detail": {"success": false, "error": {"code": "AUTH_2001", "message": "Token 无效或已过期"}}}
```

或

```
{"detail": {"success": false, "error": {"code": "AUTH_2000", "message": "缺少认证凭证"}}}
```

### 排查步骤

#### Step 1: 确认请求是否携带 Token

```javascript
// 在浏览器控制台检查
console.log(localStorage.getItem('access_token'))
// 应该有类似: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Step 2: 验证 Token 格式

```bash
# JWT Token 由三部分组成: header.payload.signature
# 格式: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c

# 解码 Token (仅解码，不验证)
echo "YOUR_TOKEN" | cut -d'.' -f2 | base64 -d | jq .

# 应该看到类似:
# {
#   "sub": "user-uuid",
#   "role": "employer",
#   "exp": 1710000000,
#   "iat": 1709990000
# }
```

#### Step 3: 检查 Token 是否过期

```bash
# 获取 Token 后计算过期时间
python3 << 'EOF'
import jwt
import time

token = "YOUR_TOKEN"
try:
    decoded = jwt.decode(token, options={"verify_signature": False})
    exp = decoded.get('exp', 0)
    now = time.time()
    if exp < now:
        print(f"❌ Token 已过期! 过期时间: {time.ctime(exp)}")
    else:
        remaining = exp - now
        print(f"✅ Token 有效，剩余 {remaining/60:.1f} 分钟过期")
        print(f"过期时间: {time.ctime(exp)}")
except Exception as e:
    print(f"❌ 解析失败: {e}")
EOF
```

#### Step 4: 验证 JWT 密钥一致性

```bash
# 检查各服务 JWT 密钥
docker compose exec user-service sh -c "echo \$JWT_SECRET_KEY"
docker compose exec job-service sh -c "echo \$JWT_SECRET_KEY"

# 应该输出相同的密钥

# 如果不一致，修改 .env 使其一致
# JWT_SECRET_KEY=your-consistent-secret-key
```

### 常见原因与解决方案

| 原因 | 解决方案 |
|------|---------|
| Token 未携带 | 前端请求添加 `Authorization: Bearer <token>` 头 |
| Token 过期 | 重新登录获取新 Token |
| JWT 密钥不一致 | 确保所有服务的 `JWT_SECRET_KEY` 相同 |
| Token 格式错误 | 检查 Bearer Token 拼写，Bearer 和 Token 之间有空格 |
| 使用了 Refresh Token | 前端应使用 Access Token，不是 Refresh Token |

### 快速修复

```bash
# 重置用户 Token (开发环境)
# 方法1: 清除前端 localStorage 后重新登录

# 方法2: 手动生成测试 Token
python3 << 'EOF'
from jose import jwt
import time

# 使用服务中的 JWT_SECRET_KEY
SECRET_KEY = "your-jwt-secret-key"
ALGORITHM = "HS256"

payload = {
    "sub": "test-user-id",
    "role": "employer",
    "email": "test@example.com",
    "type": "access",
    "iat": int(time.time()),
    "exp": int(time.time()) + 3600  # 1小时后过期
}

token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
print(f"Test Token:\n{token}")
EOF
```

---

## 3. Kafka 消息未消费

### 问题描述

- 事件发布成功，但下游服务没有收到消息
- 日志显示 `offset committed` 但没有实际处理
- 消费者组 lag 持续增长

### 排查步骤

#### Step 1: 检查 Kafka 是否正常运行

```bash
# 检查 Kafka 容器状态
docker compose ps kafka

# 测试 Kafka 连接
docker compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# 检查 Kafka 日志
docker compose logs kafka | grep -i "started\|error\|exception" | tail -20
```

#### Step 2: 检查 Topic 是否存在

```bash
# 列出所有 Topic
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# 查看特定 Topic 详情
docker compose exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic match.completed

# 检查各分区的最新 offset 和消费者 offset
docker compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group highermatch-group
```

#### Step 3: 检查消费者是否运行

```bash
# 查看消费者服务日志
docker compose logs -f matching-service

# 搜索消费相关日志
docker compose logs matching-service | grep -i "consume\|kafka\|offset\|commit"

# 检查是否有错误
docker compose logs matching-service | grep -i "error\|exception\|fail"
```

#### Step 4: 手动发送测试消息

```bash
# 创建测试 Topic
docker compose exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create \
  --topic test.topic \
  --partitions 1 \
  --replication-factor 1

# 发送测试消息
echo "test message" | docker compose exec -T kafka \
  kafka-console-producer \
  --bootstrap-server localhost:9092 \
  --topic test.topic

# 消费测试消息
docker compose exec kafka \
  kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic test.topic \
  --from-beginning
```

#### Step 5: 检查服务消费者配置

```bash
# 进入消费者服务
docker compose exec matching-service sh

# 检查环境变量
env | grep -i kafka

# 应该看到:
# KAFKA_BOOTSTRAP_SERVERS=kafka:29092
# KAFKA_CONSUMER_GROUP=highermatch-matching
```

### 常见原因与解决方案

| 原因 | 解决方案 |
|------|---------|
| Kafka 未启动 | `docker compose up -d kafka zookeeper` |
| Topic 不存在 | 手动创建或检查 `auto.create.topics.enable=true` |
| Consumer Group 不同 | 检查环境变量 `KAFKA_CONSUMER_GROUP` |
| 消费者代码异常 | 检查服务日志，修复异常 |
| Offset 提交后消息未处理 | 重置 offset 或从 beginning 消费 |
| 网络问题 | 确认 `kafka:29092` 可从服务容器内访问 |

### 快速修复

```bash
# 重置消费者 Group 的 Offset (慎用!)
docker compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group highermatch-group \
  --topic match.completed \
  --reset-offsets \
  --to-earliest \
  --execute

# 重启消费者服务
docker compose restart matching-service

# 清空 Topic 重新测试 (开发环境)
docker compose exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --delete \
  --topic match.completed

# 重建 Topic
docker compose exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create \
  --topic match.completed \
  --partitions 3 \
  --replication-factor 1
```

### 完整排查脚本

```bash
#!/bin/bash
# 保存为: scripts/kafka-debug.sh

echo "=== Kafka Debug Report ==="
echo ""

echo "1. Kafka Container Status:"
docker compose ps kafka
echo ""

echo "2. Topic List:"
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null
echo ""

echo "3. Consumer Group Status:"
docker compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --all-groups \
  --describe 2>/dev/null
echo ""

echo "4. Recent Kafka Logs (last 20 lines):"
docker compose logs kafka --tail=20
echo ""

echo "5. Services consuming from Kafka:"
docker compose ps | grep -E "SERVICE|CONSUMER" | awk '{print $1}'
```

---

## 4. Qdrant 检索返回空

### 问题描述

- 向量检索返回空结果 `{"results": []}`
- 相似度分数全部为 0
- 候选人推荐列表为空

### 排查步骤

#### Step 1: 检查 Qdrant 是否正常运行

```bash
# 检查 Qdrant 容器状态
docker compose ps qdrant

# 测试 Qdrant 健康检查
curl http://localhost:6333/healthz

# 应该返回: {"status":"ok"}
```

#### Step 2: 检查 Collection 是否存在

```bash
# 列出所有 Collections
curl http://localhost:6333/collections

# 检查特定 Collection
curl http://localhost:6333/collections/candidates

# 响应示例:
# {
#   "result": {
#     "collections": [
#       {
#         "name": "candidates",
#         "vectors_count": 1000
#       }
#     ],
#     "count": 1
#   }
# }
```

#### Step 3: 检查 Collection 详情

```bash
# 获取 Collection 详细信息
curl http://localhost:6333/collections/candidates

# 检查 points 数量
# vectors_count 应该 > 0
```

#### Step 4: 测试向量检索

```bash
# 使用 Python 测试检索
python3 << 'EOF'
import requests
import numpy as np

QDRANT_URL = "http://localhost:6333"
COLLECTION = "candidates"

# 创建一个随机查询向量 (128维度)
query_vector = np.random.randn(128).tolist()

# 执行搜索
response = requests.post(
    f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
    json={
        "vector": query_vector,
        "limit": 5,
        "with_payload": True
    }
)

result = response.json()

if result.get("result"):
    print(f"✅ 检索成功! 找到 {len(result['result'])} 个结果")
    for i, r in enumerate(result["result"]):
        print(f"  {i+1}. ID: {r['id']}, Score: {r['score']:.4f}")
else:
    print(f"❌ 检索返回空: {result}")

# 检查 Collection 统计
stats_response = requests.get(f"{QDRANT_URL}/collections/{COLLECTION}")
stats = stats_response.json()
print(f"\nCollection 状态: {stats.get('result', {}).get('status')}")
EOF
```

#### Step 5: 检查 Embedding 服务

```bash
# 检查 embedding-service 日志
docker compose logs embedding-service | tail -30

# 检查是否正确生成向量
docker compose logs embedding-service | grep -i "embedding\|vector"
```

### 常见原因与解决方案

| 原因 | 解决方案 |
|------|---------|
| Qdrant 未启动 | `docker compose up -d qdrant` |
| Collection 未创建 | 调用初始化脚本 |
| 向量维度不匹配 | 检查 embedding 维度设置 |
| 向量未正确插入 | 检查 embedding-service 日志 |
| 过滤条件太严格 | 简化搜索条件测试 |

### 快速修复

```bash
# 1. 重启 Qdrant
docker compose restart qdrant
sleep 5

# 2. 检查 Qdrant 日志
docker compose logs qdrant | tail -20

# 3. 重新初始化 Collection (如果需要)
# 方式1: 调用 API
curl -X PUT http://localhost:6333/collections/candidates \
  -H 'Content-Type: application/json' \
  --data-raw '{
    "vectors": {
      "size": 128,
      "distance": "Cosine"
    }
  }'

# 4. 重新生成所有候选人的向量 (需要后台处理)
docker compose exec embedding-service python scripts/reindex_candidates.py

# 5. 验证 Collection
curl http://localhost:6333/collections/candidates
```

### 完整诊断脚本

```bash
#!/bin/bash
# 保存为: scripts/qdrant-debug.sh

echo "=== Qdrant Debug Report ==="
echo ""

echo "1. Qdrant Health:"
curl -s http://localhost:6333/healthz
echo ""

echo "2. Collections List:"
curl -s http://localhost:6333/collections | jq '.result.collections[]?.name'
echo ""

echo "3. Collection Details:"
for collection in candidates jobs; do
  echo "  --- $collection ---"
  result=$(curl -s "http://localhost:6333/collections/$collection")
  count=$(echo $result | jq '.result.vectors_count // 0')
  echo "  Vectors Count: $count"
  status=$(echo $result | jq -r '.result.status // "unknown"')
  echo "  Status: $status"
done
echo ""

echo "4. Qdrant Container Logs (last 10 lines):"
docker compose logs qdrant --tail=10
echo ""

echo "5. Embedding Service Status:"
docker compose ps embedding-service
docker compose logs embedding-service --tail=5
```

---

## 🆘 其他问题

### 服务启动失败

```bash
# 查看所有服务日志
docker compose logs --tail=100 > debug.log

# 查看特定服务
docker compose logs service-name --tail=50

# 重启所有服务
docker compose restart
```

### 数据库连接失败

```bash
# 检查 PostgreSQL
docker compose exec postgres pg_isready -U highermatch

# 连接数据库
docker compose exec postgres psql -U highermatch -d highermatch_dev

# 检查连接数
docker compose exec postgres psql -U highermatch -d highermatch_dev -c "SELECT count(*) FROM pg_stat_activity;"
```

### 端口被占用

```bash
# 检查端口占用
lsof -i :8001  # user-service
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# 杀死占用进程
kill -9 <PID>
```

---

## 📞 获取帮助

如果以上方法无法解决问题：

1. **收集诊断信息**: 运行上述排查脚本，保存输出
2. **检查日志**: `docker compose logs > all-logs.txt`
3. **联系团队**: 在 Slack #highermatch-support 频道提问

---

<p align="center">
  <strong>保持冷静，逐一排查，问题终会解决</strong>
</p>
