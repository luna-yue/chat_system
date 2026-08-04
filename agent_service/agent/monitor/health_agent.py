"""HealthAgent — 持续探测服务端口/HTTP, 状态变化发事件"""

import json
import socket

from agent.core.agent_loop import AgentLoop
from agent.core.event_bus import Event
from agent.monitor.config import SERVICES


def _check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False


def _check_http(host: str, port: int, timeout: float = 2.0) -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(f"http://{host}:{port}/", timeout=timeout)
        return True
    except Exception:
        return False


class HealthAgent(AgentLoop):
    def __init__(self, bus, interval: float):
        super().__init__("health_agent", bus, interval)
        self._cache = {}

    def detect(self) -> dict:
        """探测所有服务: 返回 {service: "up"/"down"/"http_timeout"}"""
        state = {}
        for svc, meta in SERVICES.items():
            port = meta["port"]
            if not _check_port("127.0.0.1", port):
                state[svc] = "down"
            elif meta["proto"] == "http" and not _check_http("127.0.0.1", port):
                state[svc] = "http_timeout"
            else:
                state[svc] = "up"
        return state

    def on_state_change(self, old: dict, new: dict):
        """服务状态变化 → 发事件

        首次 (old=None) 只建立基线, 不刷屏 (常态下线不算故障).
        只有从 up → down/timeout (真故障) 或 down → up (恢复) 才发事件.
        """
        for svc in SERVICES:
            old_state = old.get(svc) if old else None
            new_state = new.get(svc)

            # 首次探测: 只记基线, 不发事件
            if old_state is None:
                continue

            # 状态没变: 不发
            if old_state == new_state:
                continue

            # 上报故障 (up→down) 和恢复 (down→up)
            if old_state in ("down", "http_timeout") or new_state in ("down", "http_timeout"):
                level = "critical" if new_state == "down" else "warning"
                event = Event.make(
                    f"health_{new_state}", svc,
                    detail=f"state: {old_state} -> {new_state}",
                    level=level,
                )
                print(f"[health_agent] 变化: {svc} {old_state} -> {new_state}")
                self.bus.publish("health", event)
