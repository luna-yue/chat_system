"""工具注册表 — 把工具名映射到真实执行函数

Planner 规则命中后, 通过注册表真正执行工具, 而不是只打印决策.
新增工具: 在 TOOL_REGISTRY 加一项即可, Planner/规则表不用改.
"""

import os
import socket
import subprocess
import time

from agent.monitor.config import SERVICES, MYSQL


# ── 阈值配置 ──
CPU_WARN_PCT = 80.0   # CPU 占用告警阈值 (%)
MEM_WARN_MB = 1024    # 内存占用告警阈值 (MB)

# ── 服务名解析 ──
# etcd 注册名 (transmite_service) → 简化名 (transmite)
_ALIASES = {f"{name}_service": name for name in SERVICES}


def _resolve(service: str) -> str:
    """解析服务名, 支持 etcd 名 (transmite_service) 和简化名 (transmite)"""
    return _ALIASES.get(service, service)


# ── 真实工具函数 ──
def check_port(service: str) -> str:
    """检查服务端口是否连通"""
    service = _resolve(service)
    meta = SERVICES.get(service)
    if not meta:
        return f"未知服务: {service}"
    try:
        s = socket.create_connection(("127.0.0.1", meta["port"]), timeout=2)
        s.close()
        return f"{service} 端口 {meta['port']} 连通"
    except Exception:
        return f"{service} 端口 {meta['port']} 不通"


def check_http(service: str) -> str:
    """检查服务 HTTP 状态"""
    service = _resolve(service)
    meta = SERVICES.get(service)
    if not meta or meta["proto"] != "http":
        return f"{service} 非 HTTP 服务"
    import urllib.request
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{meta['port']}/", timeout=2)
        return f"{service} HTTP 正常"
    except Exception:
        return f"{service} HTTP 超时"


def grep_log(service: str, pattern: str = "ERROR|FATAL") -> str:
    """搜索服务日志中的错误"""
    service = _resolve(service)
    meta = SERVICES.get(service)
    if not meta or not meta.get("log"):
        return f"服务 {service} 无日志配置"
    import re
    try:
        with open(meta["log"], "r", errors="ignore") as f:
            matches = [l.strip() for l in f if re.search(pattern, l)]
        return f"{service} 匹配 {pattern}: {len(matches)} 条" + \
               ("\n" + "\n".join(matches[-5:]) if matches else "")
    except FileNotFoundError:
        return f"{service} 日志不存在"


def mysql_status() -> str:
    """MySQL 运行状态"""
    try:
        r = subprocess.run(
            ["mysqladmin", "-h" + MYSQL["host"], "-u" + MYSQL["user"],
             "-p" + MYSQL["password"], "status"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() or r.stderr.strip()
    except Exception as e:
        return f"mysqladmin 失败: {e}"


def redis_info() -> str:
    """Redis 运行状态"""
    try:
        r = subprocess.run(["redis-cli", "info", "memory", "clients", "stats"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return f"redis-cli 失败: {r.stderr.strip()}"
        keep = []
        for line in r.stdout.splitlines():
            if any(k in line for k in
                   ["used_memory_human", "connected_clients", "keyspace_hits"]):
                keep.append(line)
        return "\n".join(keep) or "Redis 无数据"
    except Exception as e:
        return f"redis-cli 失败: {e}"


def check_process(service: str) -> str:
    """检查服务进程是否存活"""
    service = _resolve(service)
    meta = SERVICES.get(service)
    if not meta:
        return f"未知服务: {service}"
    try:
        r = subprocess.run(["pgrep", "-f", f"{service}_server"],
                           capture_output=True, text=True, timeout=5)
        pids = [p for p in r.stdout.split() if p.strip()]
        if pids:
            return f"{service} 进程存活: PIDs={','.join(pids)}"
        return f"{service} 进程不存在"
    except Exception as e:
        return f"pgrep 失败: {e}"


def check_cpu_mem(service: str) -> str:
    """检查服务进程 CPU/内存占用, 超阈值时告警"""
    service = _resolve(service)
    meta = SERVICES.get(service)
    if not meta:
        return f"未知服务: {service}"
    try:
        r = subprocess.run(
            ["ps", "-o", "pid,%cpu,%mem,rss", "-C", f"{service}_server", "--sort=-%cpu"],
            capture_output=True, text=True, timeout=5,
        )
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        if len(lines) <= 1:
            return f"{service} 进程不存在"
        header = lines[0]
        procs = lines[1:4]
        # 解析 CPU/内存, 超阈值告警
        warnings = []
        for p in procs:
            parts = p.split()
            if len(parts) >= 4:
                try:
                    cpu = float(parts[1])
                    mem = float(parts[2])
                    rss_mb = int(parts[3]) // 1024
                    if cpu > CPU_WARN_PCT:
                        warnings.append(f"  ⚠️ PID {parts[0]} CPU {cpu}% 超过 {CPU_WARN_PCT}% 阈值")
                    if rss_mb > MEM_WARN_MB:
                        warnings.append(f"  ⚠️ PID {parts[0]} 内存 {rss_mb}MB 超过 {MEM_WARN_MB}MB 阈值")
                except ValueError:
                    pass
        result = "\n".join([header] + procs)
        if warnings:
            result += "\n" + "\n".join(warnings)
        else:
            result += "\n  ✅ 资源占用正常"
        return result
    except Exception as e:
        return f"ps 失败: {e}"


def discover_services() -> str:
    """通过 etcd 发现所有已注册的服务实例"""
    try:
        r = subprocess.run(
            ["etcdctl", "--endpoints", "http://127.0.0.1:2379",
             "get", "/service/", "--prefix"],
            capture_output=True, text=True, timeout=5,
        )
        lines = r.stdout.strip().split("\n")
        pairs = []
        for i in range(0, len(lines) - 1, 2):
            key, value = lines[i].strip(), lines[i + 1].strip()
            svc = key.split("/")[2] if len(key.split("/")) > 2 else key
            pairs.append(f"{svc} → {value}")
        return "\n".join(pairs) if pairs else "etcd 无服务注册"
    except Exception as e:
        return f"etcdctl 失败: {e}"


def tail_log(service: str, lines: int = 20) -> str:
    """查看服务日志最近 N 行"""
    service = _resolve(service)
    meta = SERVICES.get(service)
    if not meta or not meta.get("log"):
        return f"服务 {service} 无日志配置"
    try:
        with open(meta["log"], "r", errors="ignore") as f:
            all_lines = f.readlines()
        return "".join(all_lines[-lines:]) or "(空日志)"
    except FileNotFoundError:
        return f"{service} 日志不存在"
    except Exception as e:
        return f"读日志失败: {e}"


def restart_service(service: str) -> str:
    """重启服务 — 杀旧进程 + 重新启动 (自愈能力)"""
    service = _resolve(service)
    meta = SERVICES.get(service)
    if not meta:
        return f"未知服务: {service}"
    bin_path = meta.get("bin")
    if not bin_path or not os.path.exists(bin_path):
        return f"服务 {service} 无二进制或路径不存在: {bin_path}"

    # 杀旧进程
    try:
        subprocess.run(["pkill", "-9", "-f", f"{service}_server"],
                       capture_output=True, timeout=5)
    except Exception:
        pass
    time.sleep(1)

    # 重新启动 (完全脱离当前会话)
    try:
        devnull = open(os.devnull, "w")
        proc = subprocess.Popen(
            [bin_path, "--run_mode=false", "--redis_host=127.0.0.1"],
            stdout=devnull, stderr=devnull,
            stdin=subprocess.DEVNULL,
            start_new_session=True,  # 独立进程组, 不被清理
        )
        time.sleep(2)
        # 验证是否起来了 (直接用 socket, 不调用注册表的 check_port)
        try:
            s = socket.create_connection(("127.0.0.1", meta["port"]), timeout=2)
            s.close()
            return f"{service} 已重启, 端口 {meta['port']} 连通 (PID={proc.pid})"
        except Exception:
            return f"{service} 启动命令已执行, 但端口 {meta['port']} 未连通"
    except Exception as e:
        return f"{service} 重启失败: {e}"


# ── 注册表 ──
# 工具名 → (函数, 参数说明)
TOOL_REGISTRY = {
    "check_port":        (check_port,       {"service": "服务名"}),
    "check_http":        (check_http,       {"service": "服务名"}),
    "check_process":     (check_process,    {"service": "服务名"}),
    "check_cpu_mem":     (check_cpu_mem,    {"service": "服务名"}),
    "grep_log":          (grep_log,         {"service": "服务名", "pattern": "正则(可选)"}),
    "tail_log":          (tail_log,         {"service": "服务名", "lines": "行数(可选)"}),
    "discover_services": (discover_services, {}),
    "mysql_status":      (mysql_status, {}),
    "redis_info":        (redis_info, {}),
    "restart_service":   (restart_service,  {"service": "服务名"}),
}


def execute(tool_name: str, args: dict) -> str:
    """执行工具, 返回结果字符串. 未知工具返回错误."""
    entry = TOOL_REGISTRY.get(tool_name)
    if not entry:
        return f"未知工具: {tool_name}"
    fn, _ = entry
    try:
        return fn(**args)
    except TypeError as e:
        return f"工具参数错误 {tool_name}: {e}"
    except Exception as e:
        return f"工具执行失败 {tool_name}: {e}"
