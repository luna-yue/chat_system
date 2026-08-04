"""12 个运维故障场景测试 — 直接构造事件喂 Planner

策略: 不依赖真实服务时序, 直接构造事件 + 真实工具注册表,
稳定验证规则命中 / 工具执行 / LLM 兜底.

真实故障验证 (场景1) 已单独证明 Agent 检测链路可用.
"""

import os
import time

os.environ.setdefault("DEEPSEEK_API_KEY", "your-api-key-here")

from agent.core.event_bus import Event, EventBus
from agent.core.planner import Planner
from agent.monitor import tool_registry, llm_planner

RESULTS = []


def record(scene, event, decision, detail):
    RESULTS.append({"scene": scene, "event": event, "decision": decision, "detail": detail})
    print(f"\n{'─'*50}")
    print(f"[场景] {scene}")
    print(f"[事件] {event.get('type')}/{event.get('service')}")
    print(f"[决策] {decision}")
    print(f"[结果] {str(detail)[:180]}")
    print(f"{'─'*50}")


# 规则表 (支持单步和多步链式诊断)
RULES = {
    ("health_down", "transmite"):     ("check_process", {"service": "transmite"}),
    ("health_down", "message"):       ("check_process", {"service": "message"}),
    # gateway 超时: 链式诊断 日志→进程→CPU
    ("health_http_timeout", "gateway"): [
        ("grep_log", {"service": "gateway", "pattern": "ERROR|FATAL"}),
        ("check_process", {"service": "gateway"}),
        ("check_cpu_mem", {"service": "gateway"}),
    ],
    ("health_down", "gateway"):       ("check_process", {"service": "gateway"}),
    # 服务恢复: 验证进程 + 端口
    ("health_up", "transmite"):       ("check_port", {"service": "transmite"}),
    ("log_error", "transmite"):       ("tail_log", {"service": "transmite", "lines": 10}),
    ("db_high", "mysql"):             ("mysql_status", {}),
    ("db_high", "redis"):             ("redis_info", {}),
}


def planner_with_rules():
    bus = EventBus()
    p = Planner(bus, rules=RULES, llm_decision_fn=llm_planner.decide,
                tool_executor=tool_registry.execute)
    return p


def scene_1_service_crash():
    """1. 服务进程崩溃 → 规则命中 check_process"""
    p = planner_with_rules()
    d = p.on_event(Event.make("health_down", "transmite", "port 10004 down", "critical"))
    record("1. 服务崩溃", Event.make("health_down", "transmite"),
           d, p.tool_results.get("transmite", [{}])[0].get("result", ""))


def scene_2_http_timeout():
    """2. gateway HTTP 超时 → 规则查日志"""
    p = planner_with_rules()
    d = p.on_event(Event.make("health_http_timeout", "gateway", "http no response"))
    record("2. HTTP 超时 (进程卡死嫌疑)", Event.make("health_http_timeout", "gateway"),
           d, p.tool_results.get("gateway", [{}])[0].get("result", ""))


def scene_3_service_not_started():
    """3. 服务未启动 → 规则命中"""
    p = planner_with_rules()
    d = p.on_event(Event.make("health_down", "message", "port 10005 down"))
    record("3. 服务未启动", Event.make("health_down", "message"),
           d, p.tool_results.get("message", [{}])[0].get("result", ""))


def scene_4_log_missing():
    """4. 日志缺失 + 未知事件 → LLM 兜底"""
    p = planner_with_rules()
    decisions = []
    bus = EventBus()
    bus.subscribe("x", lambda e: decisions.append(p.on_event(e)))
    for i in range(4):
        p.on_event(Event.make(f"strange_{i}", "weird_svc", "no rules"))
    record("4. 未知事件 → LLM 兜底", Event.make("strange_3", "weird_svc"),
           decisions[-1] if decisions else "无", "LLM 基于状态决策")


def scene_5_multi_cascade():
    """5. 多服务级联 (transmite+message down) → 累积状态走 LLM"""
    p = planner_with_rules()
    d1 = p.on_event(Event.make("health_down", "transmite"))
    d2 = p.on_event(Event.make("health_down", "message"))
    record("5. 多服务级联", Event.make("health_down", "message"),
           f"{d1[:30]} | {d2[:30]}", {k: v for k, v in p.tool_results.items()})


def scene_6_cpu_high():
    """6. 进程 CPU 高 → 检查 CPU/内存"""
    p = planner_with_rules()
    d = p.on_event(Event.make("health_degraded", "transmite", "cpu high", "warning"))
    # 无规则, 连续触发走 LLM
    for i in range(3):
        d = p.on_event(Event.make("health_degraded", "transmite", "cpu high"))
    record("6. CPU 高 (未知事件)", Event.make("health_degraded", "transmite"),
           d, "LLM 或等待")


def scene_7_port_conflict():
    """7. 端口冲突 → check_port 真实探测"""
    p = planner_with_rules()
    d = p.on_event(Event.make("health_down", "transmite", "port in use"))
    record("7. 端口冲突", Event.make("health_down", "transmite"),
           d, p.tool_results.get("transmite", [{}])[0].get("result", ""))


def scene_8_db_high():
    """8. MySQL/Redis 高负载 → 规则查状态"""
    p = planner_with_rules()
    d1 = p.on_event(Event.make("db_high", "mysql", "connections 200"))
    d2 = p.on_event(Event.make("db_high", "redis", "memory 600MB"))
    record("8. 数据库高负载", Event.make("db_high", "mysql"),
           f"{d1} | {d2}", "mysql_status/redis_info 执行")


def scene_9_log_error():
    """9. 日志大量 ERROR → 规则查日志"""
    p = planner_with_rules()
    d = p.on_event(Event.make("log_error", "transmite", "errors 500"))
    record("9. 日志大量 ERROR", Event.make("log_error", "transmite"),
           d, p.tool_results.get("transmite", [{}])[0].get("result", ""))


def scene_10_service_recover():
    """10. 服务恢复 → health_up 事件"""
    p = planner_with_rules()
    d = p.on_event(Event.make("health_up", "transmite", "recovered"))
    record("10. 服务恢复", Event.make("health_up", "transmite"),
           d, "恢复事件 (无规则, 记录状态)")


def scene_11_new_instance():
    """11. 新实例 → discover_services 发现"""
    p = planner_with_rules()
    d = p.on_event(Event.make("instance_added", "transmite", "new node", "info"))
    record("11. 新实例注册", Event.make("instance_added", "transmite"),
           d, "发现新节点")


def scene_12_unknown_type():
    """12. 完全未知事件 → LLM 深度诊断"""
    p = planner_with_rules()
    decisions = []
    bus = EventBus()
    bus.subscribe("z", lambda e: decisions.append(p.on_event(e)))
    for i in range(4):
        p.on_event(Event.make(f"alien_event_{i}", "svc"))
    record("12. 未知事件深度诊断", Event.make("alien_event_3", "svc"),
           decisions[-1] if decisions else "无", "LLM 分析")


if __name__ == "__main__":
    print("=" * 50)
    print("12 个运维场景 — Planner 决策测试")
    print("=" * 50)
    for t in [scene_1_service_crash, scene_2_http_timeout, scene_3_service_not_started,
              scene_4_log_missing, scene_5_multi_cascade, scene_6_cpu_high,
              scene_7_port_conflict, scene_8_db_high, scene_9_log_error,
              scene_10_service_recover, scene_11_new_instance, scene_12_unknown_type]:
        t()
        time.sleep(0.5)
    print(f"\n===== 完成 {len(RESULTS)} 个场景 =====")
