"""Agent 服务入口 — FastAPI HTTP 服务, Phase 2: +RAG"""

from fastapi import FastAPI

from models import ChatRequest, ChatResponse
from prompt import build_system_prompt, build_rag_prompt
from llm_client import chat as llm_chat
from rag.retriever import get_retriever
import config

app = FastAPI(
    title="Agent Service",
    description="智能客服 LLM + RAG 代理服务 — Phase 2",
    version="2.0.0",
)

# 启动时加载检索引擎 (加载 BGE 模型 + 连接 Milvus + 构建 BM25 索引)
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
    RAG 增强聊天:
    1. BM25 + 向量混合检索 Top5 FAQ
    2. 将检索结果注入 Prompt
    3. LLM 基于真实 FAQ 生成回复
    """
    # 1. 检索相关 FAQ
    docs = retriever.search(req.message, top_k=5)

    # 2. 构建 RAG Prompt
    if docs:
        context = "\n\n---\n\n".join([d["text"] for d in docs])
        messages = build_rag_prompt(context, req.message)
    else:
        # 无结果时降级为纯 LLM
        messages = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": req.message},
        ]

    # 3. 调 LLM
    reply, tokens = llm_chat(messages)

    return ChatResponse(reply=reply, model=config.LLM_MODEL, tokens_used=tokens)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.SERVICE_HOST,
        port=config.SERVICE_PORT,
        log_level="info",
    )
