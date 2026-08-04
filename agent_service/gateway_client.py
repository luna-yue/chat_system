"""Agent → Gateway HTTP 客户端 (复用已有的 C++ 后端服务)"""

import requests
import user_pb2  # protobuf Python 桩

GW = "http://127.0.0.1:9000"


def login(nickname: str, password: str = "123456") -> str | None:
    """登录, 返回 session_id"""
    req = user_pb2.UserLoginReq()
    req.request_id = "agent"
    req.nickname = nickname
    req.password = password
    try:
        r = requests.post(
            f"{GW}/service/user/username_login",
            data=req.SerializeToString(),
            headers={"Content-Type": "application/x-protobuf"},
            timeout=5,
        )
        rsp = user_pb2.UserLoginRsp()
        rsp.ParseFromString(r.content)
        return rsp.login_session_id if rsp.success else None
    except Exception:
        return None


def get_user_info(user_id: str) -> dict | None:
    """查询用户信息 (调用已有的 User 服务)"""
    req = user_pb2.GetUserInfoReq()
    req.request_id = "agent"
    req.user_id = user_id
    try:
        r = requests.post(
            f"{GW}/service/user/get_user_info",
            data=req.SerializeToString(),
            headers={"Content-Type": "application/x-protobuf"},
            timeout=5,
        )
        rsp = user_pb2.GetUserInfoRsp()
        rsp.ParseFromString(r.content)
        if rsp.success:
            u = rsp.user_info
            return {
                "user_id": u.user_id,
                "nickname": u.nickname,
                "phone": u.phone,
                "description": u.description,
            }
        return None
    except Exception:
        return None


def get_chat_sessions(user_id: str, session_id: str) -> list[dict] | None:
    """
    查询用户的聊天会话列表 (调用已有的 Friend 服务)
    注: 需要构造一个有效的登录 session, 或直接用 user_id 调用 friend 服务
    """
    import friend_pb2

    req = friend_pb2.GetChatSessionListReq()
    req.request_id = "agent"
    req.session_id = session_id
    req.user_id = user_id
    try:
        r = requests.post(
            f"{GW}/service/friend/get_chat_session_list",
            data=req.SerializeToString(),
            headers={"Content-Type": "application/x-protobuf"},
            timeout=5,
        )
        rsp = friend_pb2.GetChatSessionListRsp()
        rsp.ParseFromString(r.content)
        if rsp.success:
            return [
                {
                    "id": c.chat_session_id,
                    "name": c.chat_session_name,
                }
                for c in rsp.chat_session_info_list
            ]
        return None
    except Exception:
        return None
