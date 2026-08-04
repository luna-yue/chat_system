"""Agent 服务入口 — FastAPI HTTP 服务, 智能客服 + 多 Agent 系统监控"""

from fastapi import FastAPI

from models import ChatRequest, ChatResponse
from agent.react_loop import run as agent_run
from agent.supervisor import run_check
from rag.retriever import get_retriever

app = FastAPI(
    title="Agent Service",
    description="智能客服 Agent + 多 Agent 系统监控",
    version="4.0.0",
)

retriever = None


@app.on_event("startup")
def startup():
    global retriever
    retriever = get_retriever()


@app.get("/health")
def health():
    return {"status": "ok", "rag": retriever is not None}


@app.post("/chat", response_model=ChatResponse)
def handle_chat(req: ChatRequest) -> ChatResponse:
    """
    Agent 模式:
    1. LLM 自主决定: 直接回答 / 调 FAQ 检索 / 调订单查询 / 转人工
    2. ReAct 循环: 思考 → 行动 → 观察 → 最多 5 轮
    """
    reply = agent_run(req.user_id, req.message)
    return ChatResponse(reply=reply, model="deepseek-chat", tokens_used=0)


@app.post("/ops", response_model=ChatResponse)
def handle_ops(req: ChatRequest) -> ChatResponse:
    """
    多 Agent 系统巡检:
    Discovery → Health → Log → DB → Report
    """
    report = run_check()
    return ChatResponse(reply=report, model="multi-agent", tokens_used=0)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8080,
        log_level="info",
    )
