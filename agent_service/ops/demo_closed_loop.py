"""企业级 AIOps 完整闭环 demo

流程: 告警 → 事故 → 诊断 → HITL审批 → 执行 → 报告 → 通知
对应真实项目: RunbookHermes / ITOps Agent 的告警→诊断→审批→执行→报告闭环
"""
import os
import sys
import time

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config

from ops.incident import IncidentManager
from ops.approval import ApprovalManager, is_high_risk
from ops.notifier import Notifier
from ops.reporter import Reporter
from agent.core.event_bus import Event, EventBus
from agent.core.planner import Planner
from agent.monitor import tool_registry, llm_planner


def main():
    print("=" * 60)
    print("企业级 AIOps 完整闭环演示")
    print("=" * 60)

    # 初始化组件
    incidents = IncidentManager()
    approvals = ApprovalManager()
    notifier = Notifier()
    reporter = Reporter()

    # 规则表: 服务崩溃 → 查进程 (低风险, 规则处理)
    rules = {
        ("health_down", "transmite"): ("check_process", {"service": "transmite"}),
    }

    # 1. 检测到故障 → 告警
    print("\n[1] 故障发生: transmite 进程被杀")
    event = Event.make("health_down", "transmite", "port 10004 down", "critical")
    notifier.alert("critical", "transmite 端口 10004 不可用")

    # 2. 创建事故 + 去重
    print("\n[2] 创建事故")
    inc = incidents.on_event(event)
    notifier.incident_created(inc)
    # 同服务重复告警 → 去重合并
    inc2 = incidents.on_event(Event.make("health_down", "transmite", "still down", "critical"))
    print(f"  去重: 同一事故 {inc.id}, 事件数 {inc.event_count}")

    # 3. 诊断 (规则命中 → 查进程)
    print("\n[3] AI 诊断")
    bus = EventBus()
    planner = Planner(bus, rules=rules, llm_decision_fn=llm_planner.decide,
                      tool_executor=tool_registry.execute)
    decision = planner.on_event(event)
    print(f"  决策: {decision}")
    # 记录证据到事故
    for results in planner.tool_results.values():
        for t in results:
            incidents.add_evidence(inc.id, t["tool"], t["result"])
    inc.status = "INVESTIGATING"

    # 4. 高危操作 → HITL 审批
    print("\n[4] 高危操作审批 (HITL)")
    # 假设需要重启 (transmite 挂了)
    req = approvals.request(inc.id, "transmite", "restart_service",
                            evidence=[t["result"] for r in planner.tool_results.values() for t in r],
                            risk="high")
    notifier.approval_pending(req)

    # 模拟人工审批
    print("\n  [人工] 查看待审批操作:")
    for r in approvals.pending_requests():
        print(f"    {r.id}: {r.service} → {r.action} (风险:{r.risk})")
    approved = approvals.approve(req.id)

    # 5. 执行 (审批通过才执行)
    print("\n[5] 执行修复 (审批通过后)")
    if approved and approved.status == "APPROVED":
        result = tool_registry.execute("restart_service", {"service": "transmite"})
        print(f"  执行: {result}")
        incidents.add_evidence(inc.id, "restart_service", result)
        incidents.set_decision(inc.id, f"重启 transmite: {result}")
        # 验证恢复
        import socket
        try:
            socket.create_connection(("127.0.0.1", 10004), timeout=2).close()
            incidents.resolve(inc.id, "端口恢复")
            notifier.incident_resolved(inc)
        except Exception:
            print("  未恢复")
    else:
        print("  审批未通过, 跳过执行")

    # 6. 事故报告
    print("\n[6] 生成事故报告")
    inc.status = "CLOSED"
    report = reporter.generate(inc)
    print(f"  报告已生成 ({len(report)} 字)")
    incidents.close(inc.id)

    # 7. 总结
    print("\n" + "=" * 60)
    print("闭环完成: 告警 → 事故 → 诊断 → 审批 → 执行 → 报告")
    print("=" * 60)


if __name__ == "__main__":
    main()
