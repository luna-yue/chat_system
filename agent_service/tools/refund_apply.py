"""Mock 退款申请工具"""


def execute(order_id: str, reason: str = "") -> str:
    """申请退款, 返回处理结果"""
    return (
        f"退款申请已提交:\n"
        f"  订单: {order_id}\n"
        f"  原因: {reason or '用户申请'}\n"
        f"  金额: ¥129.00 (原路退回)\n"
        f"  预计到账: 1-3 个工作日\n"
        f"  退款编号: RF{order_id[-4:]}2026\n"
    )
