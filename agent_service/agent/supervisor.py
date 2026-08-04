"""Supervisor — 多 Agent 编排器

调度流程:
  1. DiscoveryAgent → 发现所有服务实例
  2. HealthAgent     → 检查各实例健康
  3. LogAgent        → 分析日志错误
  4. DBAgent         → 检查 MySQL/Redis
  5. ReportAgent     → 汇总生成诊断报告
"""

from llm_client import chat_with_tools
from agent.sub_agents import (
    discovery_agent,
    health_agent,
    log_agent,
    db_agent,
    report_agent,
)


def _run_agent(system_prompt: str, tools: list, user_task: str, max_steps: int = 4) -> str:
    """运行单个子 Agent 的 ReAct 循环, 返回最终文本回复"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_task},
    ]
    for _ in range(max_steps):
        reply = chat_with_tools(messages, tools)
        tool_calls = reply.get("tool_calls")
        if tool_calls:
            messages.append(reply["message"])
            for tc in tool_calls:
                name = tc["function"]["name"]
                args = tc["function"].get("arguments", {})
                result = _dispatch(tc["function"]["name"], args)
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
            continue
        return reply["content"]
    return "子 Agent 执行超时"


def _dispatch(tool_name: str, args: dict) -> str:
    """把工具名分发给对应子 Agent 的 execute_tool"""
    for mod in (discovery_agent, health_agent, log_agent, db_agent):
        if tool_name in [t["function"]["name"] for t in mod.TOOLS]:
            return mod.execute_tool(tool_name, args)
    return f"未知工具: {tool_name}"


def run_check() -> str:
    """完整巡检: 发现 → 健康 → 日志 → 数据库 → 报告"""
    print("[Supervisor] Step 1: DiscoveryAgent 发现服务...")
    discovery_result = _run_agent(
        discovery_agent.SYSTEM_PROMPT, discovery_agent.TOOLS,
        "请发现所有运行中的服务实例"
    )

    print("[Supervisor] Step 2: HealthAgent 健康检查...")
    health_result = _run_agent(
        health_agent.SYSTEM_PROMPT, health_agent.TOOLS,
        "请检查所有服务的健康状态"
    )

    print("[Supervisor] Step 3: LogAgent 日志分析...")
    log_result = _run_agent(
        log_agent.SYSTEM_PROMPT, log_agent.TOOLS,
        "请扫描所有服务的错误日志并总结",
        max_steps=6,  # 日志深挖需要多轮工具调用
    )

    print("[Supervisor] Step 4: DBAgent 数据库监控...")
    db_result = _run_agent(
        db_agent.SYSTEM_PROMPT, db_agent.TOOLS,
        "请检查 MySQL 和 Redis 的运行状态"
    )

    print("[Supervisor] Step 5: ReportAgent 生成报告...")
    context = report_agent.build_context(discovery_result, health_result, log_result, db_result)
    report = _run_agent(
        report_agent.SYSTEM_PROMPT, report_agent.TOOLS,
        f"请根据以下检查结果生成诊断报告:\n\n{context}",
        max_steps=3,
    )

    return f"## 巡检结果\n\n{report}"
