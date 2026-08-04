"""真实故障场景集成测试:
启动 HealthAgent, transmite 故障 → 规则命中 → 真实执行 check_port/grep_log
"""
import os
import signal
import subprocess
import threading
import time

from agent.core.event_bus import EventBus
from agent.core.planner import Planner
from agent.monitor import tool_registry
from agent.monitor.health_agent import HealthAgent

# 规则表: 事件 → 真实工具
RULES = {
    ("health_down", "transmite"):     ("check_port", {"service": "transmite"}),
    ("health_http_timeout", "gateway"): ("grep_log", {"service": "gateway"}),
}

bus = EventBus()
planner = Planner(bus, rules=RULES, tool_executor=tool_registry.execute)


def handler(event):
    print(f"  [Planner] {planner.on_event(event)}")


bus.subscribe("health", handler)

agent = HealthAgent(bus, 3)
agent.start()


def kill_transmite():
    time.sleep(5)
    with open("/tmp/tm_pid.txt") as f:
        pid = int(f.read().strip())
    try:
        os.kill(pid, signal.SIGKILL)
        print(f"[test] killed transmite {pid}")
    except Exception as e:
        print(f"[test] kill failed: {e}")


threading.Thread(target=kill_transmite, daemon=True).start()

time.sleep(12)
agent.stop()
print("\n=== 工具执行结果 ===")
for svc, results in planner.tool_results.items():
    for r in results:
        print(f"  {svc} → {r['tool']}: {r['result'][:100]}")
print("[test] done")
