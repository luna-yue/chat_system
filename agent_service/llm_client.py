"""LLM API 调用封装 — DeepSeek Chat (OpenAI 兼容格式)"""

import requests

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
)


def chat(messages: list[dict]) -> tuple[str, int]:
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
