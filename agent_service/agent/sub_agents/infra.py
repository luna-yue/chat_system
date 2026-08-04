"""监控基础设施 — etcd 发现 / 端口探测 / 日志读取 / MySQL / Redis 状态"""

import json
import re
import socket
import subprocess
import time
import urllib.request
from functools import lru_cache

ETCD_HOST = "127.0.0.1"
ETCD_PORT = 2379

# 服务名 (注册名) → (服务名中文, 端口, 协议)
SERVICES = {
    "gateway":   {"port": 9000,  "proto": "http", "desc": "API网关"},
    "user":      {"port": 10003, "proto": "brpc", "desc": "用户服务"},
    "friend":    {"port": 10006, "proto": "brpc", "desc": "好友服务"},
    "transmite": {"port": 10004, "proto": "brpc", "desc": "消息转发"},
    "message":   {"port": 10005, "proto": "brpc", "desc": "消息存储"},
    "file":      {"port": 10002, "proto": "brpc", "desc": "文件服务"},
    "speech":    {"port": 10001, "proto": "brpc", "desc": "语音识别"},
    "es_store":  {"port": 10007, "proto": "brpc", "desc": "ES索引"},
}

# 注册名 → 简化名
ETCD_NAME_MAP = {
    "gateway_service": "gateway", "user_service": "user",
    "friend_service": "friend", "transmite_service": "transmite",
    "message_service": "message", "file_service": "file",
    "speech_service": "speech", "es_store_service": "es_store",
}

LOG_PATHS = {
    "gateway":   "/home/luna/chat_system/build/gateway_server.log",
    "user":      "/home/luna/chat_system/build/user_server.log",
    "friend":    "/home/luna/chat_system/build/friend_server.log",
    "transmite": "/home/luna/chat_system/build/transmite_server.log",
    "message":   "/home/luna/chat_system/build/message_server.log",
    "file":      "/home/luna/chat_system/build/file_server.log",
    "speech":    "/home/luna/chat_system/build/speech_server.log",
    "es_store":  "/home/luna/chat_system/build/es_store_server.log",
}

# 每次巡检查询间隔
DISCOVERY_TTL = 30  # 秒


# ── etcd 服务发现 (etcdctl, 一次批量查询) ──
_discovery_cache = {"ts": 0, "data": None}


def _run_cmd(cmd: list, timeout: float = 5.0) -> str:
    """执行命令并返回 stdout"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f"__CMD_ERROR__: {e}"


def discover_services(use_cache: bool = True) -> dict:
    """查询 etcd 所有服务实例, 返回 {service: [{host, port, instance_id}]}"""
    global _discovery_cache
    now = time.time()
    if use_cache and _discovery_cache["data"] and now - _discovery_cache["ts"] < DISCOVERY_TTL:
        return _discovery_cache["data"]

    output = _run_cmd(
        ["etcdctl", "--endpoints", f"http://{ETCD_HOST}:{ETCD_PORT}",
         "get", "/service/", "--prefix"]
    )
    if not output or output.startswith("__CMD_ERROR__"):
        return {"error": output or "etcd 查询无结果"}

    # 输出格式: key \n value \n key \n value ...
    lines = output.split("\n")
    result = {}
    for i in range(0, len(lines) - 1, 2):
        key = lines[i].strip()
        value = lines[i + 1].strip()
        if not key or not value:
            continue
        parts = key.strip("/").split("/")
        if len(parts) < 3:
            continue
        raw_name = parts[1]
        svc_name = ETCD_NAME_MAP.get(raw_name, raw_name.replace("_service", ""))
        instance_id = parts[2]
        host, _, port = value.partition(":")
        result.setdefault(svc_name, []).append({
            "host": host, "port": int(port) if port else 0, "id": instance_id,
        })

    _discovery_cache = {"ts": now, "data": result}
    return result


def get_service_status() -> dict:
    """合并 etcd 注册信息 + 端口探测, 返回每个服务完整状态"""
    registered = discover_services()
    status = {}
    for svc_name, meta in SERVICES.items():
        etcd_instances = registered.get(svc_name, [])
        port = meta["port"]
        alive = check_port("127.0.0.1", port)
        http = {}
        if meta["proto"] == "http":
            http = check_http("127.0.0.1", port)
        status[svc_name] = {
            "desc": meta["desc"],
            "port": port,
            "registered": len(etcd_instances),
            "instances": [f"{i['host']}:{i['port']}" for i in etcd_instances],
            "port_alive": alive,
            "http": http,
            "state": "running" if alive else "down",
        }
    return status


# ── TCP 端口探测 ──
def check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False


def check_http(host: str, port: int, timeout: float = 2.0) -> dict:
    import time
    t0 = time.time()
    try:
        req = urllib.request.urlopen(f"http://{host}:{port}/", timeout=timeout)
        latency_ms = (time.time() - t0) * 1000
        return {"status": "ok", "http_code": req.status, "latency_ms": round(latency_ms, 1)}
    except Exception:
        latency_ms = (time.time() - t0) * 1000
        return {"status": "timeout", "latency_ms": round(latency_ms, 1)}


# ── 日志读取 ──
def tail_log(service: str, lines: int = 50) -> str:
    path = LOG_PATHS.get(service)
    if not path:
        return f"未知服务: {service}"
    try:
        with open(path, "r", errors="ignore") as f:
            all_lines = f.readlines()
        return "".join(all_lines[-lines:]) or "(空日志)"
    except FileNotFoundError:
        return f"日志不存在: {path}"
    except Exception as e:
        return f"读日志失败: {e}"


def grep_log(service: str, pattern: str = "ERROR|FATAL", limit: int = 20) -> str:
    path = LOG_PATHS.get(service)
    if not path:
        return f"未知服务: {service}"
    try:
        import re
        with open(path, "r", errors="ignore") as f:
            matches = [l.strip() for l in f if re.search(pattern, l)]
        total = len(matches)
        return f"匹配 {pattern}: 共 {total} 条\n" + "\n".join(matches[-limit:])
    except FileNotFoundError:
        return f"日志不存在: {path}"
    except Exception as e:
        return f"grep 失败: {e}"


def scan_all_logs() -> str:
    """扫描所有服务日志的错误数, 返回概览"""
    services = list(LOG_PATHS.keys())
    out = []
    for svc in services:
        result = grep_log(svc, "ERROR|FATAL", limit=3)
        first_line = result.split("\n")[0]
        out.append(f"  {svc}: {first_line}")
    return "\n".join(out)


# ── MySQL / Redis 状态 ──
def mysql_status() -> str:
    try:
        r = subprocess.run(
            ["mysqladmin", "-h127.0.0.1", "-uroot", "-p968745321", "status"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() or r.stderr.strip()
    except Exception as e:
        return f"mysqladmin 失败: {e}"


def redis_info() -> str:
    """Redis 状态: 内存 / 连接数 / 命中率, 逐 section 查询"""
    sections = {
        "memory": ["used_memory_human", "used_memory_peak_human"],
        "clients": ["connected_clients", "total_connections_received", "blocked_clients"],
        "stats": ["keyspace_hits", "keyspace_misses", "total_commands_processed", "expired_keys"],
    }
    try:
        keep = []
        for section, keys in sections.items():
            r = subprocess.run(
                ["redis-cli", "info", section], capture_output=True, text=True, timeout=5,
            )
            if r.returncode != 0:
                continue
            for line in r.stdout.splitlines():
                if any(k in line for k in keys):
                    keep.append(line)
        # 计算命中率
        hits = misses = None
        for line in keep:
            if line.startswith("keyspace_hits:"):
                hits = int(line.split(":")[1])
            elif line.startswith("keyspace_misses:"):
                misses = int(line.split(":")[1])
        if hits is not None and misses is not None and (hits + misses) > 0:
            keep.append(f"hit_rate: {hits/(hits+misses)*100:.1f}%")
        return "\n".join(keep) or "Redis 无数据"
    except Exception as e:
        return f"redis-cli 失败: {e}"
