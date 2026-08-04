"""DBAgent — 持续监控 MySQL/Redis, 指标异常发事件"""

import subprocess

from agent.core.agent_loop import AgentLoop
from agent.core.event_bus import Event
from agent.monitor.config import MYSQL, REDIS


class DBAgent(AgentLoop):
    def __init__(self, bus, interval: float, thresholds: dict = None):
        super().__init__("db_agent", bus, interval)
        # 阈值可配置, 默认: 连接数 > 50 告警, Redis 内存 > 500MB 告警
        self.thresholds = thresholds or {
            "mysql_conn": 50,
            "redis_mem_mb": 500,
        }

    def detect(self) -> dict:
        """探测 MySQL/Redis, 返回关键指标"""
        state = {"mysql": self._mysql_conn(), "redis": self._redis_mem()}
        return state

    def _mysql_conn(self) -> int:
        try:
            r = subprocess.run(
                ["mysqladmin", "-h" + MYSQL["host"], "-u" + MYSQL["user"],
                 "-p" + MYSQL["password"], "status"],
                capture_output=True, text=True, timeout=5,
            )
            # "Threads: 5  Questions: 1000 ..."
            for part in r.stdout.split():
                if part.startswith("Threads:"):
                    return int(part.split(":")[1])
            return 0
        except Exception:
            return -1

    def _redis_mem(self) -> int:
        """返回 Redis 内存 MB"""
        try:
            r = subprocess.run(
                ["redis-cli", "info", "memory"], capture_output=True, text=True, timeout=5,
            )
            for line in r.stdout.splitlines():
                if line.startswith("used_memory:"):
                    return int(line.split(":")[1]) // (1024 * 1024)
            return 0
        except Exception:
            return -1

    def on_state_change(self, old: dict, new: dict):
        # MySQL 连接数超阈值
        conn = new.get("mysql", 0)
        if conn > self.thresholds["mysql_conn"]:
            event = Event.make("db_high", "mysql", detail=f"connections: {conn}", level="critical")
            print(f"[db_agent] MySQL 连接数高: {conn}")
            self.bus.publish("db", event)

        # Redis 内存超阈值
        mem = new.get("redis", 0)
        if mem > self.thresholds["redis_mem_mb"]:
            event = Event.make("db_high", "redis", detail=f"memory: {mem}MB", level="warning")
            print(f"[db_agent] Redis 内存高: {mem}MB")
            self.bus.publish("db", event)
