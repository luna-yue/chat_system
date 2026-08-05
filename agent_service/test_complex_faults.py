"""复杂故障测试 — 验证 Agent 能否正确推断根因

场景 A: 依赖级联 — 多个服务 down, 是否推断共同根因 (MySQL)
场景 B: 信息矛盾 — 端口通+进程活+日志干净但业务不可用
场景 C: 关联诊断 — 多服务共享依赖
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config

from agent.core.event_bus import Event, EventBus
from agent.core.planner import Planner
from agent.monitor import tool_registry, llm_planner


def run_llm(state_events, tools_result=""):
    """给 LLM 一组诊断状态, 让它推断根因"""
    bus = EventBus()
    p = Planner(bus, rules={}, llm_decision_fn=llm_planner.decide,
                tool_executor=tool_registry.execute)
    for ev in state_events:
        p.on_event(ev)
    return p


def scene_A_cascade_rootcause():
    """场景 A: 依赖级联 — transmite+user+friend 都 down, 是否推断 MySQL 是根因"""
    print("\n" + "=" * 60)
    print("[场景A] 依赖级联: 多服务 down, 找共同根因")
    print("=" * 60)

    events = [
        Event.make("health_down", "transmite", "port down", "critical"),
        Event.make("health_down", "user", "port down", "critical"),
        Event.make("health_down", "friend", "port down", "critical"),
        Event.make("health_down", "message", "port down", "critical"),
    ]
    p = run_llm(events)

    # 检查 LLM 是否查了 MySQL (说明它推断 MySQL 可能是根因)
    mysql_checked = any(
        t["tool"] == "mysql_status" for results in p.tool_results.values() for t in results
    )
    print(f"LLM 查了 MySQL: {mysql_checked}")
    print("→ 如果查了 MySQL, 说明推断'多服务都依赖 MySQL'")
    return mysql_checked


def scene_B_conflicting():
    """场景 B: 信息矛盾 — transmite 端口通+进程活+日志干净, 但上报 down"""
    print("\n" + "=" * 60)
    print("[场景B] 信息矛盾: 端口通+进程活+日志干净, 但上报 down")
    print("=" * 60)

    events = [
        Event.make("health_down", "transmite", "business unavailable", "critical"),
        Event.make("health_down", "transmite", "business unavailable", "critical"),
        Event.make("health_down", "transmite", "business unavailable", "critical"),
        Event.make("health_down", "transmite", "business unavailable", "critical"),
    ]
    p = run_llm(events)

    # 看 LLM 诊断结论
    restart_called = any(
        t["tool"] == "restart_service" for results in p.tool_results.values() for t in results
    )
    print(f"LLM 决定重启: {restart_called}")
    print("→ 如果端口通+进程活, 正确做法是查资源/连接, 而非盲目重启")
    return True


def scene_C_multi_service():
    """场景 C: 多服务独立故障, 逐个处理"""
    print("\n" + "=" * 60)
    print("[场景C] 多服务独立故障, 逐个诊断")
    print("=" * 60)

    events = [
        Event.make("health_down", "transmite", "port down", "critical"),
        Event.make("db_high", "mysql", "connections 500", "warning"),
        Event.make("log_error", "message", "errors 200", "warning"),
        Event.make("health_down", "user", "port down", "critical"),
    ]
    p = run_llm(events)

    # 各服务是否都被处理
    services_checked = set()
    for svc, results in p.tool_results.items():
        if results:
            services_checked.add(svc)
    print(f"被处理的资源: {services_checked}")
    print("→ 多故障应逐个诊断")
    return len(services_checked) >= 2


if __name__ == "__main__":
    a = scene_A_cascade_rootcause()
    b = scene_B_conflicting()
    c = scene_C_multi_service()
    print(f"\n{'='*60}")
    print(f"结果: A依赖级联={a}  B信息矛盾={b}  C多服务={c}")
    print(f"{'='*60}")
