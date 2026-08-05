"""真实级联自愈: transmite + message 都挂, LLM 逐个拉起

步骤:
  1. 确保两个服务都停
  2. 发事件给 LLM
  3. 验证 LLM 是否逐个 restart 拉起
"""
import os
import signal
import subprocess
import time

import config  # 加载 key

from agent.core.event_bus import Event, EventBus
from agent.core.planner import Planner
from agent.monitor import tool_registry, llm_planner


def stop_service(name):
    """确保服务没在跑"""
    r = subprocess.run(["pgrep", "-f", f"build/{name}/{name}_server"],
                       capture_output=True, text=True)
    for pid in [int(p) for p in r.stdout.split() if p.isdigit()]:
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"  stopped {name} PID={pid}")
        except Exception as e:
            print(f"  stop {name} fail: {e}")
    time.sleep(1)


def main():
    print("=== 停止 transmite 和 message ===")
    stop_service("transmite")
    stop_service("message")

    bus = EventBus()
    planner = Planner(bus, rules={}, llm_decision_fn=llm_planner.decide,
                      tool_executor=tool_registry.execute)
    decisions = []
    bus.subscribe("health", lambda e: decisions.append(planner.on_event(e)))

    print("\n=== 发两个服务的事件 ===")
    for i in range(4):
        planner.on_event(Event.make("health_down", "transmite", "port down", "critical"))
        planner.on_event(Event.make("health_down", "message", "port down", "critical"))

    time.sleep(3)
    r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
    transmite_up = "10004" in r.stdout
    message_up = "10005" in r.stdout
    print(f"\ntransmite 端口恢复: {transmite_up}")
    print(f"message 端口恢复: {message_up}")
    print(f"\n→ {'✅ 级联自愈成功' if transmite_up and message_up else '❌ 未全部恢复'}")


if __name__ == "__main__":
    main()
