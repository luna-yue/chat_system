"""监控配置 — 集中管理, 不散落. 后续可替换为 config.yaml 加载"""

# 服务配置: 服务名 → 探测信息
SERVICES = {
    "gateway":   {"port": 9000,  "proto": "http",  "log": "/home/luna/chat_system/build/gateway_server.log",
                  "bin": "/home/luna/chat_system/build/gateway/gateway_server"},
    "user":      {"port": 10003, "proto": "brpc",  "log": "/home/luna/chat_system/build/user_server.log",
                  "bin": "/home/luna/chat_system/build/user/user_server"},
    "friend":    {"port": 10006, "proto": "brpc",  "log": "/home/luna/chat_system/build/friend_server.log",
                  "bin": "/home/luna/chat_system/build/friend/friend_server"},
    "transmite": {"port": 10004, "proto": "brpc",  "log": "/home/luna/chat_system/build/transmite_server.log",
                  "bin": "/home/luna/chat_system/build/transmite/transmite_server"},
    "message":   {"port": 10005, "proto": "brpc",  "log": "/home/luna/chat_system/build/message_server.log",
                  "bin": "/home/luna/chat_system/build/message/message_server"},
    "file":      {"port": 10002, "proto": "brpc",  "log": "/home/luna/chat_system/build/file_server.log",
                  "bin": "/home/luna/chat_system/build/file/file_server"},
    "speech":    {"port": 10001, "proto": "brpc",  "log": "/home/luna/chat_system/build/speech_server.log",
                  "bin": "/home/luna/chat_system/build/speech/speech_server"},
    "es_store":  {"port": 10007, "proto": "brpc",  "log": "/home/luna/chat_system/build/es_store_server.log",
                  "bin": "/home/luna/chat_system/build/es_store/es_store_server"},
}

# MySQL / Redis
MYSQL = {"host": "127.0.0.1", "user": "root", "password": "968745321"}
REDIS = {"host": "127.0.0.1", "port": 6379}

# etcd
ETCD = {"host": "127.0.0.1", "port": 2379}

# Agent 探测间隔 (秒)
INTERVAL = {
    "health": 5,
    "log":    10,
    "db":     15,
}

# Planner 阈值
PLANNER = {
    "max_rounds": 8,     # 最多处理几轮
    "llm_threshold": 4,  # 连续几个事件规则命中不了 → 走 LLM
}
