"""自愈测试: transmite 被杀 → LLM 诊断 → 调 restart_service 拉起

验证 Agent 从"只诊断"升级到"能恢复服务".
"""
import os
import signal
import subprocess
import time

os.environ.setdefault("DEEPSEEK_API_KEY", "your-api-key-here")

from agent.core.event_bus import Event, EventBus
from agent.core.planner import Planner
from agent.monitor import tool_registry, llm_planner


def kill_transmite():
    r = subprocess.run(["pgrep", "-f", "build/transmite/transmite_server"],
                       capture_output=True, text=True)
    pids = [int(p) for p in r.stdout.split() if p.isdigit()]
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"killed transmite PID={pid}", flush=True)
        except Exception as e:
            print(f"kill {pid} fail: {e}", flush=True)
    time.sleep(1)


def main():
    # 1. kill transmite
    kill_transmite()

    # 2. 构造事件触发 LLM 兜底 (规则表空, 全走 LLM)
    bus = EventBus()
    planner = Planner(bus, rules={}, llm_decision_fn=llm_planner.decide,
                      tool_executor=tool_registry.execute)
    decisions = []
    bus.subscribe("health", lambda e: decisions.append(planner.on_event(e)))

    print("=== 触发 4 个 health_down 事件, 走 LLM 兜底 ===", flush=True)
    for i in range(4):
        planner.on_event(Event.make("health_down", "transmite",
                                    "port 10004 down", "critical"))

    print("\n=== 检查 transmite 是否被自愈拉起 ===", flush=True)
    r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
    if "10004" in r.stdout:
        print("✅ transmite 端口 10004 已监听 (自愈成功!)", flush=True)
    else:
        print("❌ transmite 未拉起", flush=True)

    print("\n=== LLM 决策历史 ===", flush=True)
    for d in decisions[-3:]:
        print(f"  {d[:120]}", flush=True)


if __name__ == "__main__":
    main()
