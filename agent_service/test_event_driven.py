"""事件驱动链路测试: 启动 HealthAgent, 中途杀 transmite, 验证事件流"""
import os
import signal
import subprocess
import threading
import time

from agent.core.event_bus import EventBus
from agent.core.planner import Planner
from agent.monitor.health_agent import HealthAgent

bus = EventBus()
planner = Planner(bus, rules={("health_down", "transmite"): ("check_redis", {})})


def handler(event):
    print(f"  [Planner] {planner.on_event(event)}")


bus.subscribe("health", handler)

agent = HealthAgent(bus, 3)
agent.start()


def kill_transmite():
    """动态找 transmite_server 进程并杀掉"""
    time.sleep(5)
    r = subprocess.run(["pgrep", "-f", "transmite_server"], capture_output=True, text=True)
    pids = [int(p) for p in r.stdout.split()]
    # 排除当前 python 进程
    pids = [p for p in pids if p != os.getpid()]
    print(f"[test] 找到 transmite PIDs: {pids}")
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"[test] killed {pid}")
        except Exception as e:
            print(f"[test] kill {pid} 失败: {e}")


threading.Thread(target=kill_transmite, daemon=True).start()

time.sleep(12)
agent.stop()
print("[test] done")
