"""LogAgent — 持续扫描错误日志, 错误数变化发事件"""

import re

from agent.core.agent_loop import AgentLoop
from agent.core.event_bus import Event
from agent.monitor.config import SERVICES


def _count_errors(path: str, pattern: str = r"ERROR|FATAL") -> int:
    """统计日志中的错误行数"""
    try:
        with open(path, "r", errors="ignore") as f:
            return sum(1 for line in f if re.search(pattern, line))
    except FileNotFoundError:
        return -1  # 日志不存在


class LogAgent(AgentLoop):
    def __init__(self, bus, interval: float):
        super().__init__("log_agent", bus, interval)

    def detect(self) -> dict:
        """扫描所有服务日志, 返回 {service: error_count}"""
        state = {}
        for svc, meta in SERVICES.items():
            path = meta.get("log")
            if path:
                state[svc] = _count_errors(path)
        return state

    def on_state_change(self, old: dict, new: dict):
        """错误数变化 → 发事件"""
        for svc in SERVICES:
            old_n, new_n = old.get(svc, 0), new.get(svc, 0)
            if old_n != new_n and new_n > 0:  # 只看出现错误
                event = Event.make(
                    "log_error", svc,
                    detail=f"error_count: {old_n} -> {new_n}",
                    level="critical",
                )
                print(f"[log_agent] 发现错误: {svc} errors={new_n}")
                self.bus.publish("log", event)
