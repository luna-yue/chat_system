"""HealthAgent — 对所有服务实例做健康检查"""

from agent.sub_agents.infra import get_service_status, SERVICES

NAME = "health_agent"
DESCRIPTION = "对所有服务实例做端口/HTTP 健康检查"

TOOLS = [
    {"type": "function", "function": {
        "name": "check_all_services",
        "description": "检查所有服务的端口连通性、HTTP 状态、etcd 注册情况",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "check_single_service",
        "description": "检查单个服务的健康状态",
        "parameters": {"type": "object", "properties": {
            "service": {"type": "string", "description": "服务名: gateway/user/friend/transmite/message/file/speech/es_store"},
        }, "required": ["service"]},
    }},
]


def execute_tool(name: str, args: dict) -> str:
    import json
    if name == "check_all_services":
        status = get_service_status()
        return json.dumps(status, ensure_ascii=False, indent=2)
    if name == "check_single_service":
        svc = args.get("service", "")
        if svc not in SERVICES:
            return f"未知服务: {svc}. 可选: {', '.join(SERVICES)}"
        status = get_service_status().get(svc, {})
        return json.dumps(status, ensure_ascii=False, indent=2)
    return f"未知工具: {name}"


SYSTEM_PROMPT = """你是健康检查 Agent。任务:
1. 调用 check_all_services 检查所有服务的端口连通性、HTTP 状态、etcd 注册情况
2. 汇总报告: 哪些服务运行正常、哪些宕机、哪些注册了但端口不通
只报告事实, 明确区分"运行中/已下线/注册异常", 不做深入诊断。"""
