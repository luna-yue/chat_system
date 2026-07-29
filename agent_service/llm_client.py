"""LLM API 调用封装 — DeepSeek Chat (OpenAI 兼容格式)"""

import json
import requests

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
)


def _make_request(messages: list[dict], tools: list[dict] = None) -> dict:
    """发送请求, 返回完整 JSON response"""
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": LLM_TEMPERATURE,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    resp = requests.post(
        f"{LLM_BASE_URL}/chat/completions",
        headers=headers,
        json=body,
        timeout=LLM_TIMEOUT,
    )
    if resp.status_code == 429:
        raise RuntimeError("rate limited")
    if resp.status_code == 401:
        raise RuntimeError("auth failed")
    resp.raise_for_status()
    return resp.json()


def chat(messages: list[dict]) -> tuple[str, int]:
    """
    调用 DeepSeek Chat API, 返回 (回复文本, token 消耗).
    失败时返回降级提示语, tokens_used=0。
    """
    try:
        data = _make_request(messages)
        reply = data["choices"][0]["message"]["content"]
        tokens = data["usage"]["total_tokens"]
        return reply.strip(), tokens
    except requests.Timeout:
        return "抱歉，服务响应超时，请稍后重试。", 0
    except requests.ConnectionError:
        return "抱歉，服务暂时不可用，请稍后重试。", 0
    except RuntimeError:
        return "抱歉，服务暂时不可用。", 0
    except Exception:
        return "抱歉，服务暂时不可用。", 0


def chat_with_tools(messages: list[dict], tools: list[dict]) -> dict:
    """
    ReAct Agent 调用: 发送 messages + tools, 返回解析结果.

    Returns:
        {"content": "..."}           — LLM 直接给出文本回复
        {"tool_calls": [...], "message": {...}} — LLM 要求调工具
    """
    try:
        data = _make_request(messages, tools)
        choice = data["choices"][0]
        msg = choice["message"]

        # 有 tool_calls
        if msg.get("tool_calls"):
            tool_calls = []
            for tc in msg["tool_calls"]:
                tool_calls.append({
                    "id": tc["id"],
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": json.loads(tc["function"]["arguments"]),
                    },
                })
            return {
                "tool_calls": tool_calls,
                "message": {"role": "assistant", "tool_calls": msg["tool_calls"]},
            }

        # 普通文本回复
        return {"content": (msg.get("content") or "").strip()}

    except requests.Timeout:
        return {"content": "抱歉，服务响应超时，请稍后重试。"}
    except Exception:
        return {"content": "抱歉，服务暂时不可用。"}
    """
    调用 DeepSeek Chat API, 返回 (回复文本, token 消耗).

    Args:
        messages: [{"role": "system", "content": "..."},
                   {"role": "user",   "content": "..."}]

    Returns:
        (reply, tokens_used): LLM 回复文本 和 token 消耗数。
        失败时返回降级提示语, tokens_used=0。
    """
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": LLM_TEMPERATURE,
    }

    try:
        resp = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=body,
            timeout=LLM_TIMEOUT,
        )

        # HTTP 错误
        if resp.status_code == 429:
            return "抱歉，当前访问量较大，请稍等片刻。", 0
        if resp.status_code == 401:
            return "服务配置错误，请联系管理员。", 0
        resp.raise_for_status()

        data = resp.json()
        reply = data["choices"][0]["message"]["content"]
        tokens = data["usage"]["total_tokens"]
        return reply.strip(), tokens

    except requests.Timeout:
        return "抱歉，服务响应超时，请稍后重试。", 0
    except requests.ConnectionError:
        return "抱歉，服务暂时不可用，请稍后重试。", 0
    except Exception:
        return "抱歉，服务暂时不可用。", 0
