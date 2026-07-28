"""系统 Prompt 模板"""

from datetime import datetime


def build_system_prompt() -> str:
    """构建系统 Prompt, 注入当前日期"""
    today = datetime.now().strftime("%Y年%m月%d日")

    return f"""你是智能客服助手。

## 行为准则
- 回答简洁明了，每次回复不超过 150 字
- 如果你不知道答案，诚实说明"抱歉，这个问题我暂时无法回答"
- 不要编造信息，不要给出不确定的建议
- 语气友好、专业，适当使用表情符号
- 如果用户问"你是谁"，回答你是智能客服助手

## 当前日期
{today}
"""


def build_rag_prompt(context: str, user_message: str) -> list[dict]:
    """构建 RAG 增强 Prompt — 注入检索到的参考文档"""
    today = datetime.now().strftime("%Y年%m月%d日")

    system = f"""你是智能客服助手。基于以下参考资料回答用户问题。

## 参考资料
{context}

## 回答规则
- 如果参考资料中有答案，直接引用并组织成简洁回复
- 如果参考资料中部分涉及，只回答有依据的部分
- 如果参考资料中没有答案，诚实说明"抱歉，我暂时无法回答这个问题"
- 不要编造参考资料中没有的信息
- 每次回复不超过 150 字
- 语气友好、专业

## 当前日期
{today}"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]


# 备用：简短版 prompt（token 更少，响应更快）
SHORT_PROMPT = (
    "你是智能客服助手。回答简洁（不超过150字），"
    "不知道就说不知道。友好、专业。当前日期：" + datetime.now().strftime("%Y-%m-%d")
)
