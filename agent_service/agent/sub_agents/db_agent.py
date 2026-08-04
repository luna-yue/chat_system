"""DBAgent — MySQL / Redis 状态监控"""

from agent.sub_agents.infra import mysql_status, redis_info

NAME = "db_agent"
DESCRIPTION = "监控 MySQL 和 Redis 的运行状态"

TOOLS = [
    {"type": "function", "function": {
        "name": "mysql_status",
        "description": "获取 MySQL 运行状态 (连接数/慢查询/吞吐)",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "redis_info",
        "description": "获取 Redis 状态 (内存/连接数/命中率)",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
]


def execute_tool(name: str, args: dict) -> str:
    if name == "mysql_status":
        return mysql_status()
    if name == "redis_info":
        return redis_info()
    return f"未知工具: {name}"


SYSTEM_PROMPT = """你是数据库监控 Agent。任务:
1. 调用 mysql_status 获取 MySQL 状态
2. 调用 redis_info 获取 Redis 状态
3. 报告: MySQL 连接数是否正常、Redis 内存使用率、命中率
关注异常值并给出可能的原因, 不做最终诊断。"""
