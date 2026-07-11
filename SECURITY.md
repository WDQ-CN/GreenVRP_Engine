# 安全修复说明

本文档描述了对 GreenVRP Engine API 进行的安全增强。

## 修复的安全漏洞

### 1. API 认证 (高危)
**问题**: API 完全开放，任何人都可调用

**修复**:
- 添加了基于 API Key 的认证机制 (`X-API-Key` 请求头)
- 添加了 JWT Token 认证支持 (Bearer Token)
- 所有核心端点（求解器、场景管理）现在需要认证
- 健康检查端点保持可选认证（公开访问）

**使用方式**:
```bash
# 使用 API Key
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/solve

# 或使用 JWT Token
curl -H "Authorization: Bearer your-jwt-token" http://localhost:8000/api/v1/solve
```

### 2. 速率限制 (高危)
**问题**: 无速率限制，易受 DoS 攻击

**修复**:
- 集成 slowapi 实现速率限制
- 不同端点有不同的限制策略：
  - 求解器端点：10 次/分钟
  - 场景管理：20 次/分钟（写操作），100 次/分钟（读操作）
  - 健康检查：60 次/分钟

**配置**:
通过环境变量自定义速率限制：
```bash
export RATE_LIMIT_SOLVER="10/minute"
export RATE_LIMIT_DEFAULT="100/minute"
```

### 3. CORS 配置过宽 (高危)
**问题**: 允许所有来源跨域请求 (`allow_origins=["*"]`)

**修复**:
- 限制为配置的允许来源列表
- 仅允许必要的 HTTP 方法
- 仅允许必要的请求头

**配置**:
```bash
export ALLOWED_ORIGINS="http://localhost:3000,https://yourdomain.com"
```

### 4. SSRF 风险 - Callback URL (高危)
**问题**: callback_url 未验证，可能被用于访问内网

**修复**:
- 仅允许 HTTPS 协议
- 阻止内网 IP 地址（私有 IP、回环地址、链路本地地址）
- 实现 URL 白名单机制
- 在发送回调前和发送时双重验证

**配置**:
```bash
export CALLBACK_URL_WHITELIST="https://example.com/callback,https://api.example.com/webhook"
```

## 环境变量配置

生产环境应设置以下环境变量：

```bash
# API 密钥（多个用逗号分隔）
export API_KEYS="your-secure-api-key-1,your-secure-api-key-2"

# JWT 配置
export JWT_SECRET_KEY="your-super-secret-key-change-this"
export JWT_TOKEN_EXPIRE_MINUTES=60

# CORS 允许的来源
export ALLOWED_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"

# Callback URL 白名单
export CALLBACK_URL_WHITELIST="https://your-callback-endpoint.com/webhook"

# 速率限制
export RATE_LIMIT_SOLVER="10/minute"
export RATE_LIMIT_DEFAULT="100/minute"
```

## 新增文件结构

```
/workspace
├── config/
│   └── security.py          # 安全配置模块
├── api/
│   ├── security/
│   │   ├── __init__.py      # 安全模块导出
│   │   ├── auth.py          # 认证逻辑（API Key + JWT）
│   │   └── rate_limit.py    # 速率限制配置
│   ├── routers/
│   │   ├── solver.py        # 已添加认证和速率限制
│   │   ├── scenarios.py     # 已添加认证和速率限制
│   │   └── health.py        # 可选认证
│   ├── services/
│   │   └── solver_service.py # 安全的回调实现
│   └── main.py              # 已更新 CORS 和速率限制
└── SECURITY.md              # 本文件
```

## 默认 API 密钥

开发环境默认 API 密钥：`green-vrp-default-key-2024`

**重要**: 生产环境必须修改此密钥！

## 测试认证

```bash
# 无认证（应返回 401）
curl http://localhost:8000/api/v1/solve -X POST -H "Content-Type: application/json" -d '{}'

# 使用默认 API Key（应成功或返回其他错误）
curl http://localhost:8000/api/v1/solve -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: green-vrp-default-key-2024" \
  -d '{"customers": [...]}'
```

## 后续建议

1. **使用 Redis**: 将任务管理器从内存存储迁移到 Redis
2. **数据库**: 使用真正的数据库替代内存存储
3. **HTTPS**: 生产环境必须使用 HTTPS
4. **日志审计**: 添加安全事件日志
5. **密钥管理**: 使用专业的密钥管理服务（如 AWS Secrets Manager）
