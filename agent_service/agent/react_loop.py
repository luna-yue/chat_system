"""ReAct Agent 决策循环 — 思考 → 行动 → 观察 → 重复"""

from agent.tools import TOOLS, execute_tool
from llm_client import chat_with_tools
from prompt import AGENT_SYSTEM_PROMPT

MAX_STEPS = 5  # 最多调用 5 次工具, 防止死循环


def run(user_id: str, user_message: str) -> str:
    """
    ReAct 循环:
    1. 构建 messages = [system_prompt, user_message]
    2. 调 LLM (带 tools 列表)
    3. 如果 LLM 返回 tool_call → 执行 → 结果追加到 messages → 回到步骤 2
    4. 如果 LLM 返回普通文本 → 结束, 返回回复
    """
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for step in range(MAX_STEPS):
        reply = chat_with_tools(messages, TOOLS)

        # 检查是否有 tool_calls
        tool_calls = reply.get("tool_calls")

        if tool_calls:
            # LLM 要求调工具
            messages.append(reply["message"])  # assistant 的 tool_call 消息

            for tc in tool_calls:
                name = tc["function"]["name"]
                args = tc["function"].get("arguments", {})
                # 注入 user_id (如果工具需要)
                if "user_id" in args:
                    args["user_id"] = user_id

                print(f"[Agent] step={step} tool={name} args={args}")
                result = execute_tool(name, args)
                print(f"[Agent] result={result[:80]}...")
                messages.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": result}
                )

            # 继续循环, LLM 会基于工具结果再思考
            continue
        else:
            # LLM 直接给了文本回复
            return reply["content"]

    return "抱歉，处理超时，请稍后重试。"
