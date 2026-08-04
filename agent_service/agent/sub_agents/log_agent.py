"""LogAgent — 分析各服务日志中的错误"""

from agent.sub_agents.infra import tail_log, grep_log, scan_all_logs, LOG_PATHS

NAME = "log_agent"
DESCRIPTION = "分析各服务日志中的错误和异常"

TOOLS = [
    {"type": "function", "function": {
        "name": "scan_all_logs",
        "description": "扫描所有服务日志, 统计 ERROR/FATAL 数量",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "tail_log",
        "description": "读取指定服务日志最后 N 行",
        "parameters": {"type": "object", "properties": {
            "service": {"type": "string", "description": "服务名"},
            "lines": {"type": "integer", "description": "行数, 默认 50"},
        }, "required": ["service"]},
    }},
    {"type": "function", "function": {
        "name": "grep_log",
        "description": "搜索指定服务日志中匹配模式的行",
        "parameters": {"type": "object", "properties": {
            "service": {"type": "string", "description": "服务名"},
            "pattern": {"type": "string", "description": "正则, 默认 ERROR|FATAL"},
        }, "required": ["service"]},
    }},
]


def execute_tool(name: str, args: dict) -> str:
    if name == "scan_all_logs":
        return scan_all_logs()
    if name == "tail_log":
        svc = args.get("service", "")
        lines = int(args.get("lines", 50))
        if svc not in LOG_PATHS:
            return f"未知服务: {svc}. 可选: {', '.join(LOG_PATHS)}"
        return tail_log(svc, lines)
    if name == "grep_log":
        svc = args.get("service", "")
        pattern = args.get("pattern", "ERROR|FATAL")
        if svc not in LOG_PATHS:
            return f"未知服务: {svc}. 可选: {', '.join(LOG_PATHS)}"
        return grep_log(svc, pattern)
    return f"未知工具: {name}"


SYSTEM_PROMPT = """你是日志分析 Agent。任务:
1. 调用 scan_all_logs 扫描所有服务的错误日志概览
2. 对错误较多的服务, 调用 tail_log 或 grep_log 查看具体错误内容
3. 报告: 哪个服务错误多、错误类型是什么、最近发生了什么异常
只报告事实和可能原因, 不做最终诊断。"""
