"""订单查询 — 读真实 MySQL, 返回用户参与的聊天会话"""

import pymysql
from agent.monitor.config import MYSQL


def execute(user_id: str) -> str:
    """查询用户参与的聊天会话 (作为"订单"展示)"""
    conn = pymysql.connect(
        host=MYSQL["host"], user=MYSQL["user"], password=MYSQL["password"],
        database="TestDB", charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT cs.chat_session_id, cs.chat_session_name "
                "FROM chat_session cs "
                "JOIN chat_session_member csm ON cs.chat_session_id = csm.session_id "
                "WHERE csm.user_id = %s LIMIT 5",
                (user_id,),
            )
            rows = cur.fetchall()
            if not rows:
                return f"用户 {user_id} 暂无会话记录。"
            lines = [f"用户 {user_id} 的会话列表:"]
            for i, (sid, name) in enumerate(rows, 1):
                lines.append(f"  {i}. 会话ID: {sid} | 名称: {name or '(未命名)'}")
            return "\n".join(lines)
    finally:
        conn.close()
