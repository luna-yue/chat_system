"""Agent 服务入口 — FastAPI HTTP 服务"""

from fastapi import FastAPI

from models import ChatRequest, ChatResponse
from prompt import build_system_prompt
from llm_client import chat as llm_chat
import config

app = FastAPI(
    title="Agent Service",
    description="智能客服 LLM 代理服务 — Phase 1",
    version="1.0.0",
)


@app.get("/health")
def health():
    """健康检查端点"""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def handle_chat(req: ChatRequest) -> ChatResponse:
    """
    处理聊天请求:
    1. 构建 messages (system prompt + user message)
    2. 调用 DeepSeek API
    3. 返回 LLM 回复
    """
    # 1. 构建消息
    system_prompt = build_system_prompt()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.message},
    ]

    # 2. 调 LLM
    reply, tokens = llm_chat(messages)

    # 3. 返回
    return ChatResponse(reply=reply, model=config.LLM_MODEL, tokens_used=tokens)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.SERVICE_HOST,
        port=config.SERVICE_PORT,
        log_level="info",
    )
