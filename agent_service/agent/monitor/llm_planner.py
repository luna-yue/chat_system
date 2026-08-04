"""真实 LLM 兜底 — 完整决策闭环

规则覆盖不了 → LLM 决策循环:
  LLM 建议调工具 → 真执行 → 结果喂回 → LLM 再推理 → 循环
  直到 LLM 得出结论 / 轮数耗尽升级人工
"""

from llm_client import chat_with_tools
from agent.monitor import tool_registry

# LLM 可调用的监控工具 (从注册表生成)
FALLBACK_TOOLS = [
    {"type": "function", "function": {"name": "check_port",
        "description": "检查服务端口是否连通",
        "parameters": {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]}}},
    {"type": "function", "function": {"name": "check_http",
        "description": "检查服务 HTTP 状态",
        "parameters": {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]}}},
    {"type": "function", "function": {"name": "check_process",
        "description": "检查服务进程是否存活",
        "parameters": {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]}}},
    {"type": "function", "function": {"name": "check_cpu_mem",
        "description": "检查服务进程 CPU/内存占用",
        "parameters": {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]}}},
    {"type": "function", "function": {"name": "grep_log",
        "description": "搜索服务日志中的错误",
        "parameters": {"type": "object", "properties": {
            "service": {"type": "string"}, "pattern": {"type": "string"}}, "required": ["service"]}}},
    {"type": "function", "function": {"name": "tail_log",
        "description": "查看服务日志最近几行",
        "parameters": {"type": "object", "properties": {
            "service": {"type": "string"}, "lines": {"type": "integer"}}, "required": ["service"]}}},
    {"type": "function", "function": {"name": "discover_services",
        "description": "通过 etcd 发现所有已注册服务",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "mysql_status",
        "description": "获取 MySQL 运行状态",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "redis_info",
        "description": "获取 Redis 运行状态",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "restart_service",
        "description": "重启指定服务 (高危操作). 确认服务进程不存在时才使用",
        "parameters": {"type": "object", "properties": {
            "service": {"type": "string", "description": "服务名"}}, "required": ["service"]}}},
]

SYSTEM_PROMPT = """你是分布式系统的运维诊断器。你会收到监控事件和诊断状态, 通过调用工具定位问题根因, 并尽可能恢复服务。

## 诊断方法
1. 分析事件, 决定先查什么 (端口? 进程? 日志? 数据库?)
2. 调用工具收集证据
3. 基于证据继续推理, 可能需要多轮工具调用
4. 证据充分后, 给出诊断结论

## 自愈能力
- 如果确认服务进程不存在 (check_process 返回"进程不存在"), 且端口不通,
  调用 restart_service 拉起服务
- 重启前必须确认进程确实不存在, 不要误杀运行中的服务 (高危操作)

## 工具 (10个)
check_port / check_http / check_process / check_cpu_mem /
grep_log / tail_log / discover_services / mysql_status / redis_info /
restart_service

## 收敛规则
- 信息不足才继续调工具, 不要重复查已确认的信息
- 证据足够 → 直接给出结论, 不要继续调工具
"""

MAX_ROUNDS = 5  # 最多 5 轮工具调用


def decide(state: dict, event: dict, tool_results: dict) -> str:
    """LLM 兜底: 决策循环, 建议→执行→回喂→再推理→结论/升级"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content":
            f"## 诊断状态 (各服务已发生的事件)\n{state}\n\n"
            f"## 已执行的工具结果\n{tool_results}\n\n"
            f"## 新事件\n{event}\n\n"
            f"请诊断: 查什么工具定位问题, 或直接给结论"},
    ]

    for round_no in range(MAX_ROUNDS):
        reply = chat_with_tools(messages, FALLBACK_TOOLS)

        if reply.get("tool_calls"):
            # 关键: 先把 assistant 的 tool_calls 追加进 messages
            messages.append(reply["message"])
            # LLM 要调工具 → 真执行 → 结果喂回
            for tc in reply["tool_calls"]:
                name = tc["function"]["name"]
                args = tc["function"].get("arguments", {})
                result = tool_registry.execute(name, args)
                print(f"    [LLM 执行] {name}({args}) = {result[:60]}")
                messages.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": result})
            continue  # LLM 看结果再推理

        # LLM 给出结论
        return f"LLM 诊断 ({round_no}轮): {reply.get('content', '')[:300]}"

    # 轮数耗尽 → 升级人工
    return "无法自动诊断, 需人工介入 (诊断轮数耗尽)"
