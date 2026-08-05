"""工具注册表 — 7 个工具: FAQ / 订单 / 物流 / 退款 / 商品 / 工单 / 人工"""

from rag.retriever import get_retriever


def _faq_search(query: str) -> str:
    retriever = get_retriever()
    docs = retriever.search(query, top_k=3)
    return "\n\n".join(f"[{d['id']}] {d['text']}" for d in docs) if docs else "未找到相关 FAQ。"


def _order_query(user_id: str) -> str:
    from tools.order_query import execute
    return execute(user_id)


def _track_logistics(tracking_no: str) -> str:
    from tools.track_logistics import execute
    return execute(tracking_no)


def _refund_apply(order_id: str, reason: str = "") -> str:
    from tools.refund_apply import execute
    return execute(order_id, reason)


def _product_info(product_name: str) -> str:
    catalog = {
        "t恤": "白色T恤 | 纯棉 | ¥129 | 尺码: S/M/L/XL | 库存: 充足",
        "运动鞋": "黑色运动鞋 | 网面透气 | ¥459 | 尺码: 38-44 | 库存: 部分缺货",
        "耳机": "蓝牙耳机 | 降噪 | ¥299 | 续航 30h | 库存: 充足",
        "手机壳": "硅胶手机壳 | 多色可选 | ¥39 | 适配 iPhone/华为/小米 | 库存: 充足",
    }
    key = product_name.lower()
    for k, v in catalog.items():
        if k in key:
            return f"商品信息: {v}"
    return f"未找到 '{product_name}' 的商品信息。可尝试: T恤、运动鞋、耳机、手机壳"


def _create_ticket(user_id: str, issue: str) -> str:
    return f"工单已创建:\n  编号: TK-2026-{hash(issue) % 10000:04d}\n  问题: {issue}\n  状态: 待处理\n  客服将在 2 小时内回复"


def _transfer_human(reason: str = "") -> str:
    return f"已转接人工客服。原因: {reason or '用户请求'}。请稍候。"


# ── 注册表 (7 工具) ──
TOOLS = [
    {"type": "function", "function": {
        "name": "faq_search",
        "description": "搜索 FAQ 知识库。用于退货/退款/物流/支付/售后等政策类问题",
        "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "搜索关键词"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "order_query",
        "description": "查询用户最近订单列表。用户问'我的订单''买了什么'时使用",
        "parameters": {"type": "object", "properties": {"user_id": {"type": "string", "description": "用户 ID"}}, "required": ["user_id"]}}},
    {"type": "function", "function": {
        "name": "track_logistics",
        "description": "根据快递单号追踪物流状态。用户问'快递到哪了''物流状态'并提供单号时使用",
        "parameters": {"type": "object", "properties": {"tracking_no": {"type": "string", "description": "快递单号"}}, "required": ["tracking_no"]}}},
    {"type": "function", "function": {
        "name": "refund_apply",
        "description": "为指定订单申请退款。用户明确说'我要退款''帮我退货退款'时使用",
        "parameters": {"type": "object", "properties": {"order_id": {"type": "string", "description": "订单编号"}, "reason": {"type": "string", "description": "退款原因"}}, "required": ["order_id"]}}},
    {"type": "function", "function": {
        "name": "product_info",
        "description": "查询商品详细信息（价格/尺码/库存）。用户问'XX商品怎么样'时使用",
        "parameters": {"type": "object", "properties": {"product_name": {"type": "string", "description": "商品名称"}}, "required": ["product_name"]}}},
    {"type": "function", "function": {
        "name": "create_ticket",
        "description": "创建客服工单，记录用户问题并分配给人工处理",
        "parameters": {"type": "object", "properties": {"user_id": {"type": "string"}, "issue": {"type": "string", "description": "问题描述"}}, "required": ["user_id", "issue"]}}},
    {"type": "function", "function": {
        "name": "transfer_human",
        "description": "转接人工客服。用户明确要求转人工时使用",
        "parameters": {"type": "object", "properties": {"reason": {"type": "string", "description": "转接原因"}}, "required": []}}},
]

TOOL_MAP = {
    "faq_search": _faq_search,
    "order_query": _order_query,
    "track_logistics": _track_logistics,
    "refund_apply": _refund_apply,
    "product_info": _product_info,
    "create_ticket": _create_ticket,
    "transfer_human": _transfer_human,
}


def execute_tool(name: str, args: dict) -> str:
    func = TOOL_MAP.get(name)
    if not func:
        return f"未知工具: {name}"
    try:
        return str(func(**args))
    except Exception as e:
        return f"工具执行失败: {e}"
