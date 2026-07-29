"""工具注册表 — 定义工具名、JSON Schema、执行函数"""

from rag.retriever import get_retriever


# ── 工具定义 ──
# 每个工具: name, description, parameters (JSON Schema), execute 函数

def _faq_search(query: str) -> str:
    """检索 FAQ 知识库"""
    retriever = get_retriever()
    docs = retriever.search(query, top_k=3)
    if not docs:
        return "未找到相关 FAQ。"
    return "\n\n".join(f"[{d['id']}] {d['text']}" for d in docs)


def _order_query(user_id: str) -> str:
    """查订单 (mock)"""
    from tools.order_query import execute
    return execute(user_id)


def _transfer_human(reason: str = "") -> str:
    """转人工客服"""
    return f"已转接人工客服。原因: {reason or '用户请求'}。请稍候，客服将尽快接入。"


# ── 注册表 ──
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "faq_search",
            "description": "搜索 FAQ 知识库。当用户询问退货/退款/物流/支付/售后等政策类问题时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词, 例如: '退货政策', '退款流程'",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "order_query",
            "description": "查询用户最近订单。当用户询问'我的订单''查物流''快递到哪了'时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户的唯一标识 ID",
                    }
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_human",
            "description": "转接人工客服。当用户明确要求'转人工'、问题超出自动客服能力范围时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "转接原因, 可选",
                    }
                },
                "required": [],
            },
        },
    },
]

TOOL_MAP = {
    "faq_search": _faq_search,
    "order_query": _order_query,
    "transfer_human": _transfer_human,
}


def execute_tool(name: str, args: dict) -> str:
    """执行指定工具, 返回结果字符串"""
    func = TOOL_MAP.get(name)
    if not func:
        return f"未知工具: {name}"
    try:
        return str(func(**args))
    except Exception as e:
        return f"工具执行失败: {e}"
