"""DiscoveryAgent — 通过 etcd 发现所有服务实例"""

from agent.sub_agents.infra import discover_services

NAME = "discovery_agent"
DESCRIPTION = "通过 etcd 服务发现获取所有微服务实例列表"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "discover_services",
            "description": "查询 etcd 获取所有已注册的服务实例 (服务名 → [{host, port, instance_id}])",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    import json
    if name == "discover_services":
        return json.dumps(discover_services(), ensure_ascii=False, indent=2)
    return f"未知工具: {name}"


SYSTEM_PROMPT = """你是分布式系统的服务发现 Agent。你的任务:
1. 调用 discover_services 获取 etcd 中所有注册的服务实例
2. 输出一份清单: 哪些服务在运行、各有多少实例、实例的 host:port
只报告事实, 不做诊断。"""
