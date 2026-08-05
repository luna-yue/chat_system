# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build System

This is a CMake-based C++ project. Build from the `build/` directory:

```bash
cd build && cmake .. -DCMAKE_BUILD_TYPE=Debug && make -j$(nproc)
```

The top-level `CMakeLists.txt` delegates to per-service subdirectories (gateway, user, friend, transmite, message, file, speech, es_store). Each service produces its own binary. Service-specific CMakeLists also define test client targets (e.g., `friend_client` for the friend service).

Protobuf and ODB code generation happens automatically as PRE_BUILD steps:
- `protoc` generates `.pb.cc`/`.pb.h` from `proto/*.proto`
- `odb` generates `-odb.hxx`/`-odb.cxx` from `odb/*.hpp`

QPS test tools (`qps_test_login/`, `qps_test_message/`) have standalone Makefiles and are built independently.

Third-party headers live in `third/include/`.

## Architecture

This is a **microservices-based instant messaging system**. All services communicate via **brpc** (Baidu RPC, `baidu_std` protocol). The API gateway exposes **HTTP** for request/response calls and **WebSocket** for real-time push notifications to connected clients.

### Service Components

| Service | Directory | Role |
|---|---|---|
| **Gateway** | `gateway/` | Dual-protocol entry point (HTTP + WebSocket). Authenticates clients via `session_id` against Redis, discovers backend services via etcd, forwards HTTP requests to backend brpc services, and pushes real-time notifications (new messages, friend events, session creation) to WebSocket clients. |
| **User** | `user/` | Registration (username + phone), login, profile CRUD (avatar, nickname, description, phone), multi-user batch info lookup. |
| **Friend** | `friend/` | Friend list, friend add/remove/apply/process, pending-event list, search users, chat session CRUD, session member list. Uses MySQL for relations and Elasticsearch for user search. |
| **Transmite** | `transmite/` | Message routing: receives a new message from the Gateway, looks up session members from MySQL, builds the full `MessageInfo` (assigns snowflake ID + timestamp + sender info via calling User service), publishes to RabbitMQ for async persistence, returns the target user list to Gateway for WebSocket push. |
| **Message** | `message/` | Message storage: get history by time range, get recent N messages, keyword search. |
| **File** | `file/` | File upload/download (single + batch). |
| **Speech** | `speech/` | Speech-to-text recognition. |
| **ES Store** | `es_store/` | Elasticsearch indexing/storage for messages. |

### Request Flow (sending a message)

```
Client --HTTP--> Gateway --brpc--> Transmite
                                       ├── brpc --> User (get sender info)
                                       ├── MySQL (get session members)
                                       └── RabbitMQ (publish for async persistence)
Transmite returns target user list + full MessageInfo to Gateway
Gateway pushes NotifyNewMessage via WebSocket to each online target
```

### Service Discovery

All backend services register themselves to **etcd** under `/service/<service_name>/<instance_id>` with their host:port. The `Discovery` class (in `common/etcd.hpp`) watches etcd prefixes and fires callbacks on `ServiceManager`, which maintains a pool of `brpc::Channel` objects per service. The Gateway and any service that calls other services use `ServiceManager::choose()` for round-robin channel selection.

### Key Infrastructure (in `common/`)

| File | Purpose |
|---|---|
| `brpc.hpp` | `ServiceManager` + `ChannelManager`: dynamic brpc channel pool fed by etcd service discovery callbacks. |
| `etcd.hpp` | `Registry` (register + keepalive via lease) and `Discovery` (watch prefix + dispatch put/del callbacks). |
| `rabbitmq.hpp` | `MQClient`: libev-based AMQP client using AMQP-CPP. Supports confirm mode, retry queue (max 3 retries), and message consumption with `ConsumeResult` (Success/Retry/Fatal) to implement reliable delivery. All channel operations run on a dedicated I/O thread. |
| `data_redis.hpp` | `Session` (login session ID → user ID), `Status` (online status), `Codes` (verification codes with 5-min TTL). Uses redis++. |
| `elasticSearch.hpp` | JsonCpp serialization helpers + `ESIndex` wrapper for Elasticsearch CRUD operations via elasticlient. |
| `snowflake.hpp` | Distributed unique ID generator (1ms precision, epoch=2023-11-15, 10-bit machine ID, 12-bit sequence). |
| `logger.hpp` | Logging wrapper. |
| `utils.hpp` | Misc utilities (UUID generation, etc.). |
| `mysql*.hpp` | ODB-based table access objects for users, chat sessions, session members, relations, friend applies, and messages. |
| `data_es.hpp` | Elasticsearch data access layer for user/message indexing. |
| `asr.hpp` | ASR (speech recognition) integration. |

### Database Schema (ODB ORM)

Object-relational mappings are in `odb/`:
- `user.hpp` — user accounts
- `relation.hpp` — friend relationships (user ↔ peer)
- `friend_apply.hpp` — pending friend requests
- `chat_session.hpp` — chat sessions (single + group)
- `chat_session_member.hpp` — session membership
- `message.hpp` — persisted messages

ODB generates SQL schemas, query support, and migration code. The friend service depends on most of these; Transmite only uses `chat_session_member`; Message uses `message`.

### Protobuf Services (in `proto/`)

All protos use package `luna` with `cc_generic_services = true`. Shared types (`UserInfo`, `ChatSessionInfo`, `MessageInfo`, `MessageContent` with oneof for text/image/file/speech) are in `base.proto`. Service protos: `user.proto`, `friend.proto`, `transmite.proto`, `message.proto`, `file.proto`, `speech.proto`, `notify.proto` (WebSocket push notifications), `gateway.proto` (HTTP endpoint definitions, but no RPC service — just the `ClientAuthenticationReq` message).

### Gateway Request Pattern

Every Gateway HTTP handler follows the same pattern:
1. Deserialize protobuf from request body
2. Extract `session_id`, look up `user_id` from Redis `Session`
3. Set `user_id` on the request
4. `ServiceManager::choose(service_name)` → brpc stub → call
5. If the backend returns success and the operation requires real-time notification (friend events, new session, new message), look up the target user's WebSocket connection via `Connection` and push a `NotifyMessage`
6. Serialize the backend response and return it

### Testing

Tests use Google Test (`gtest`) + `gflags` for configuration. Test clients (e.g., `friend/test/friend_client.cpp`, `user/test/user_client.cpp`) connect to a running etcd instance, discover services, and make brpc calls. Run with:

```bash
./friend_client --etcd_host=http://127.0.0.1:2379 --base_service=/service --user_service=/service/user_service
```

MySQL integration tests live in `user/test/mysql_test/`.

### Key Dependencies

`brpc`, `protobuf`, `etcd-cpp-api`, `redis++` (sw::redis), `AMQP-CPP` + `libev`, `elasticlient` + `cpr` + `jsoncpp`, `ODB` + `libodb-mysql`, `websocketpp`, `httplib` (header-only), `spdlog` + `fmt`, `gflags`, `gtest`, `boost` (system + date-time), `OpenSSL`.
