"""场景5: 多服务级联自愈 — LLM 处理多个服务故障

模拟: transmite 崩溃 + message 未启动
预期:
  - transmite (低风险) → LLM 确认后重启
  - message (低风险) → LLM 尝试重启 (或报告未部署)
"""
import os
import signal
import subprocess
import time

import config  # 加载 .env / 环境变量, 提供 LLM_API_KEY

from agent.core.event_bus import Event, EventBus
from agent.core.planner import Planner
from agent.monitor import tool_registry, llm_planner


def main():
    # 1. kill transmite
    r = subprocess.run(["pgrep", "-f", "build/transmite/transmite_server"],
                       capture_output=True, text=True)
    for pid in [int(p) for p in r.stdout.split() if p.isdigit()]:
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"killed transmite PID={pid}")
        except Exception as e:
            print(f"kill fail: {e}")
    time.sleep(1)

    # 2. 发多个服务事件
    bus = EventBus()
    planner = Planner(bus, rules={}, llm_decision_fn=llm_planner.decide,
                      tool_executor=tool_registry.execute)
    decisions = []
    bus.subscribe("health", lambda e: decisions.append(planner.on_event(e)))

    print("=== 发多服务事件: transmite 崩溃 + message 未启动 ===")
    for i in range(2):
        planner.on_event(Event.make("health_down", "transmite", "port down", "critical"))
        planner.on_event(Event.make("health_down", "message", "port down", "critical"))

    # 3. 检查结果
    time.sleep(2)
    r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
    transmite_up = "10004" in r.stdout
    # message 有没有被尝试重启
    message_restart = any(
        t["tool"] == "restart_service" and "message" in str(t.get("args", {}))
        for results in planner.tool_results.values() for t in results
    )
    print(f"\ntransmite 端口恢复: {transmite_up}")
    print(f"message 被尝试重启: {message_restart}")
    print(f"→ {'✅ 级联处理完成' if transmite_up else '❌ transmite 未恢复'}")


if __name__ == "__main__":
    main()
