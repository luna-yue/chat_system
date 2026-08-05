"""风险分级决策测试:
低风险故障 → LLM 自动自愈 (重启服务)
高风险故障 → LLM 只报告, 不自动处理
"""
import os
import signal
import subprocess
import time

import config  # 加载 .env / 环境变量 (敏感信息不硬编码)

from agent.core.event_bus import Event, EventBus
from agent.core.planner import Planner
from agent.monitor import tool_registry, llm_planner

# 规则表: 高风险故障让 LLM 决策 (不自动重启)
RULES = {}


def make_planner():
    bus = EventBus()
    p = Planner(bus, rules=RULES, llm_decision_fn=llm_planner.decide,
                tool_executor=tool_registry.execute)
    return p


def test_low_risk_self_heal():
    """低风险: 服务崩溃 → LLM 应该自愈重启"""
    print("=" * 50)
    print("[低风险] 服务崩溃 → 应自愈重启")
    print("=" * 50)

    # kill transmite
    r = subprocess.run(["pgrep", "-f", "build/transmite/transmite_server"],
                       capture_output=True, text=True)
    pids = [int(p) for p in r.stdout.split() if p.isdigit()]
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"  killed transmite PID={pid}")
        except Exception as e:
            print(f"  kill fail: {e}")
    time.sleep(1)

    # 触发 LLM 兜底 (4 次未命中事件)
    p = make_planner()
    for i in range(4):
        p.on_event(Event.make("health_down", "transmite", "port down", "critical"))

    # 检查是否自愈
    time.sleep(2)
    r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
    healed = "10004" in r.stdout
    # 检查是否调用了 restart
    restarted = any(
        t["tool"] == "restart_service" for results in p.tool_results.values() for t in results
    )
    print(f"\n  调用了 restart_service: {restarted}")
    print(f"  transmite 端口 10004 重新监听: {healed}")
    print(f"  → {'✅ 自愈成功' if healed and restarted else '❌ 未自愈'}")
    return healed and restarted


def test_high_risk_report_only():
    """高风险: DB 高负载 → LLM 只报告, 不应调用 restart"""
    print("\n" + "=" * 50)
    print("[高风险] DB 高负载 → 应只报告不重启")
    print("=" * 50)

    p = make_planner()
    for i in range(4):
        p.on_event(Event.make("db_high", "mysql", "connections 200", "warning"))

    # 检查是否误调用了 restart
    restarted = any(
        t["tool"] == "restart_service" for results in p.tool_results.values() for t in results
    )
    called_mysql = any(
        t["tool"] == "mysql_status" for results in p.tool_results.values() for t in results
    )
    print(f"  调用了 mysql_status: {called_mysql}")
    print(f"  误调用 restart_service: {restarted}")
    print(f"  → {'✅ 只报告未误重启' if not restarted and called_mysql else '❌ 风险判断错误'}")
    return not restarted and called_mysql


if __name__ == "__main__":
    ok1 = test_low_risk_self_heal()
    ok2 = test_high_risk_report_only()
    print(f"\n{'='*50}")
    print(f"风险分级: {'✅ 全部通过' if ok1 and ok2 else '❌ 有失败'}")
    print(f"{'='*50}")
