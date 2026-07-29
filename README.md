# Chat System — 分布式即时通讯 + AI Agent 智能客服

[![v1.0.0](https://img.shields.io/badge/v1.0.0-baseline-blue)](https://github.com/luna-yue/chat_system/releases/tag/v1.0.0)
[![v1.1.0](https://img.shields.io/badge/v1.1.0-performance-green)](https://github.com/luna-yue/chat_system/releases/tag/v1.1.0)

C++ 微服务架构的即时通讯系统，支持单聊/群聊/文件/语音，后期嫁接 Python AI Agent 引擎实现智能客服。

---

## 架构总览

```
                           ┌──────────┐
                           │  Client  │
                           └────┬─────┘
                                │ HTTP / WS
                           ┌────▼──────┐
                           │  Gateway  │  ← 路由 / 鉴权 / WS 推送
                           └──┬─┬─┬─┬──┘
                              │ │ │ │
         ┌────────────────────┼─┼─┼─┼──────────────┐
         │           ┌────────┘ │ │ └─────┐        │
    ┌────▼──┐   ┌───▼──┐  ┌───▼─▼─▼──┐  │  ┌──────▼──┐ ┌────────┐
    │ User  │   │Friend│  │Transmite │  │  │ Message │ │ES Store│
    └──┬─┬──┘   └──┬─┬─┘  └┬─┬─┬───┬┘   │  └────┬────┘ └───┬────┘
       │ │         │ │      │ │ │   │   │       │          │
       │ │    ┌────┘ │      │ │ │   │   │       │          │
   ┌───▼─▼────▼──┐   │      │ │ │   │   │  ┌────▼────┐ ┌──▼─────┐
   │ MySQL+Redis │   │      │ │ │   │   │  │  MySQL  │ │  ES    │
   └─────────────┘   │      │ │ │   │   │  └─────────┘ └────────┘
                     │      │ │ │   │   │
                ┌────▼──────▼─▼─▼───▼───▼────┐
                │        RabbitMQ           │
                │  msg → Message 消费落 MySQL │
                │  msg → ES Store 消费落 ES  │
                │  push→ Gateway 消费推 WS   │
                └───────────────────────────┘

              ┌──────────┐
              │ Agent    │  ← Python (LLM + RAG)
              │ (FastAPI)│
              └──────────┘
```

### 依赖关系（基于代码实测）

| 服务 | MySQL | Redis | RabbitMQ | ES | 调用其他服务 |
|------|-------|-------|----------|-----|------------|
| **Gateway** | ✅ | ✅ | ✅ (push) | | User, Friend, Transmite, Message, File, Speech |
| **User** | ✅ | ✅ | | ✅ | File (头像) |
| **Friend** | ✅ | ✅ | | ✅ | User, Message |
| **Transmite** | ✅ | ✅ | ✅ (生产 msg) | | User |
| **Message** | ✅ | | ✅ (消费 msg) | ✅ | User, File |
| **File** | | | | | — |
| **Speech** | | | | | — |
| **ES Store** | | | ✅ (消费 msg) | ✅ | — |

### 消息流

```
Client → Gateway → Transmite
                     ├── 查群成员: Redis (缓存) / MySQL (回源)
                     ├── 取发件人: Redis (UserInfoCache) / User RPC (回源)
                     └── 拼 MessageInfo → publish RabbitMQ
                                           ├── Message 服务 消费 → 落 MySQL
                                           └── ES Store 消费 → 落 ES 索引

Gateway → 遍历 target_list → publish RabbitMQ push 队列
       → Gateway consumer 异步消费 → WebSocket 推送给在线用户
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| RPC 框架 | **brpc** (百度开源, bthread 协程) |
| 服务发现 | **etcd** |
| 消息队列 | **RabbitMQ** (AMQP, topic exchange) |
| 数据库 | **MySQL** (ODB ORM) |
| 缓存 | **Redis** (redis++, Cache-Aside, 64 分片锁) |
| 搜索引擎 | **Elasticsearch** |
| 协议 | Protobuf / WebSocket |
| AI 引擎 | **Python FastAPI** + DeepSeek + BM25 |
| 部署 | **Docker Compose** (12 容器) |
| 构建 | CMake (C++17) |

---

## 快速开始

```bash
# 1. 准备依赖 (首次)
./scripts/prepare-deps.sh

# 2. 构建镜像 + 启动全栈
docker compose build
docker compose up -d

# 3. 检查状态
docker compose ps

# HTTP API → :9000  WebSocket → :9001  Agent → :8080
```

---

## 性能优化

Message QPS: **320 → 826 (+158%)**

| 步骤 | 改动 | QPS |
|------|------|-----|
| 初始 | MySQL 直查 + 嵌套 RPC | 320 |
| 1 | SessionMemberCache (群成员 Redis 缓存) | 385 |
| 2 | UserInfoCache (消除嵌套 RPC) | 364→2149(brpc裸) |
| 3 | Gateway 插桩 → 删无效日志 | 994 |
| 4 | MQ 异步推送 (100 WS 在线 +55%) | 826 |



---

## AI Agent 模块

| 能力 | 技术 |
|------|------|
| LLM 对话 | DeepSeek Chat API |
| RAG 检索 | BM25 + 50 条 FAQ 知识库 |
| 工具调用 | ReAct 循环 (订单查询/FAQ检索/人工转接) |
| 评估 | 262 条测试集, 工具准确率 80.9% |


---

## 目录

```
├── gateway/          # HTTP + WebSocket 网关
├── user/             # 用户服务
├── friend/           # 好友 + 群聊管理
├── transmite/        # 消息路由 + 扇出推送
├── message/          # 消息存储
├── file/             # 文件上传/下载
├── speech/           # 语音识别
├── es_store/         # ES 索引
├── common/           # 共享库 (brpc/etcd/redis/mysql/mq)
├── proto/            # Protobuf 定义
├── agent_service/    # Python AI Agent
├── scripts/          # 部署脚本
├── docs/             # 文档
├── docker-compose.yml
└── Dockerfile
```

---

## 水平扩展验证

在同等硬件环境下，通过逐步增加 Gateway 和 Transmite 实例数，用 C++ QPS 压测工具
(20 线程, 5000 请求, 100 人群) 测试消息发送接口的吞吐变化。

| 部署 | QPS | 说明 |
|------|-----|------|
| 1 Gateway + 1 Transmite | ~644 | 基准 |
| 1 Gateway + 2 Transmite | ~588 | Transmite 加实例无提升 |
| 2 Gateway + 1 Transmite | ~674 | Gateway 加实例小幅提升 |
| 2 Gateway + 2 Transmite | ~645 | 几乎无变化 |

**结论**：应用层水平扩展无法线性提升 QPS，当前瓶颈在共享中间件
(单实例 MySQL/Redis/RabbitMQ)。要突破天花板需要对中间件做读写分离或集群化。

多网关部署需配置不同的 `--gateway_id`，MQ push 队列按实例隔离:
```bash
./gateway_server --gateway_id=gw1  # 队列: push_queue_gw_gw1
./gateway_server --gateway_id=gw2  # 队列: push_queue_gw_gw2
```

---

## License

MIT
