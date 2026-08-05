"""场景2: HTTP 超时自愈 — LLM 确认进程不存在后自动重启

模拟: transmite 进程被杀, 上报 http_timeout 事件
预期: LLM 查进程 → 确认不存在 → 调 restart_service 拉起
"""
import os
import signal
import subprocess
import time

import config  # 加载 .env / 环境变量 (敏感信息不硬编码)

from agent.core.event_bus import Event, EventBus
from agent.core.planner import Planner
from agent.monitor import tool_registry, llm_planner


def main():
    # 1. kill transmite (模拟卡死/崩溃)
    r = subprocess.run(["pgrep", "-f", "build/transmite/transmite_server"],
                       capture_output=True, text=True)
    pids = [int(p) for p in r.stdout.split() if p.isdigit()]
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"killed transmite PID={pid}")
        except Exception as e:
            print(f"kill fail: {e}")
    time.sleep(1)

    # 2. 发 http_timeout 事件 (规则表空, 走 LLM)
    bus = EventBus()
    planner = Planner(bus, rules={}, llm_decision_fn=llm_planner.decide,
                      tool_executor=tool_registry.execute)
    decisions = []
    bus.subscribe("health", lambda e: decisions.append(planner.on_event(e)))

    print("=== 发 health_http_timeout 事件 (走 LLM) ===")
    for i in range(4):
        planner.on_event(Event.make("health_http_timeout", "transmite",
                                    "http no response", "critical"))

    # 3. 检查是否自愈
    time.sleep(2)
    r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
    healed = "10004" in r.stdout
    restarted = any(
        t["tool"] == "restart_service" for results in planner.tool_results.values() for t in results
    )
    print(f"\n调用了 restart_service: {restarted}")
    print(f"transmite 端口 10004 重新监听: {healed}")
    print(f"\n→ {'✅ HTTP超时自愈成功' if healed and restarted else '❌ 未自愈'}")


if __name__ == "__main__":
    main()
