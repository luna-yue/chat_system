"""Pydantic 请求/响应模型 — 自动校验 + 生成 OpenAPI 文档"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """客户端发来的聊天请求"""

    user_id: str = Field(..., description="用户唯一标识")
    message: str = Field(
        ..., min_length=1, max_length=2000, description="用户输入, 1-2000 字符"
    )


class ChatResponse(BaseModel):
    """Agent 返回的聊天回复"""

    reply: str = Field(..., description="LLM 生成的回复文本")
    model: str = Field(default="", description="使用的模型名称")
    tokens_used: int = Field(default=0, description="本次消耗的 token 数")
