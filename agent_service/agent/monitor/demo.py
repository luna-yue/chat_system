"""事件驱动多 Agent 运维 — 单进程 demo

启动 3 个监控 Agent 持续探测, Planner 订阅事件做决策.
运行 N 秒后停止, 打印 Planner 的决策历史.
"""

import time

from agent.core.event_bus import EventBus
from agent.core.planner import Planner
from agent.monitor.config import INTERVAL
from agent.monitor.health_agent import HealthAgent
from agent.monitor.log_agent import LogAgent
from agent.monitor.db_agent import DBAgent


def build_rules():
    """switch case 规则表: (事件type, 服务) → 决策描述"""
    return {
        ("health_down", "gateway"):     ("grep_log", {"service": "gateway"}),
        ("health_down", "transmite"):   ("check_redis", {"service": "transmite"}),
        ("health_http_timeout", "gateway"): ("check_process", {"service": "gateway"}),
        ("log_error", "gateway"):       ("mysql_status", {}),
        ("db_high", "mysql"):           ("check_conn", {"service": "transmite"}),
    }


def llm_fallback(state, event):
    """LLM 兜底 — 简单模拟, 后续接真实 DeepSeek"""
    svc = event.get("service")
    history = state.get(svc, [])
    return f"复杂情况: {svc} 历史事件 {history} → 需 LLM 深度诊断"


def main(run_seconds: int = 20):
    bus = EventBus()

    # Planner 订阅所有频道
    planner = Planner(bus, rules=build_rules(), llm_decision_fn=llm_fallback)
    decisions = []

    def handler(event, planner=planner):
        d = planner.on_event(event)
        decisions.append(d)
        print(f"  [Planner] {d}")

    bus.subscribe("health", handler)
    bus.subscribe("log", handler)
    bus.subscribe("db", handler)

    # 启动监控 Agent (持续探测, 状态变化才发事件)
    agents = [
        HealthAgent(bus, INTERVAL["health"]),
        LogAgent(bus, INTERVAL["log"]),
        DBAgent(bus, INTERVAL["db"]),
    ]
    for a in agents:
        a.start()

    print(f"\n=== 事件驱动运维运行 {run_seconds}s ===")
    time.sleep(run_seconds)

    for a in agents:
        a.stop()

    print("\n=== Planner 决策历史 ===")
    for d in decisions:
        print(d)
    print(f"\n共 {len(decisions)} 个决策, 规则命中率: "
          f"{sum(1 for d in decisions if d.startswith('[规则]'))}/{len(decisions)}")


if __name__ == "__main__":
    main()
