"""RAG 检索引擎 — BM25 (词法匹配), 零外部模型依赖"""

import json
import re
from pathlib import Path
from typing import Optional

from rank_bm25 import BM25Okapi

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class Retriever:
    """BM25 关键词检索, 适合 FAQ 精确匹配场景"""

    def __init__(self, faq_path: str = None):
        if faq_path is None:
            faq_path = DATA_DIR / "faq.json"
        with open(faq_path, "r", encoding="utf-8") as f:
            self._faq = json.load(f)
        for item in self._faq:
            item["text"] = f"Q: {item['question']}\nA: {item['answer']}"

        self._texts = [item["text"] for item in self._faq]
        self._ids = [item["id"] for item in self._faq]
        tokenized = [self._tokenize(t) for t in self._texts]
        self._bm25 = BM25Okapi(tokenized)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """中英文混合分词: 中文逐字 + 英文/数字按词"""
        tokens = []
        tokens.extend(re.findall(r"[一-鿿]", text))  # 中文逐字
        tokens.extend(re.findall(r"[a-zA-Z0-9]+", text.lower()))  # 英文数字
        return tokens if tokens else text.split()  # fallback

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """BM25 检索 TopK, 返回 [{"id":..., "text":..., "score":...}]"""
        tokenized = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized)

        # 按分排序取 TopK
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in ranked[:top_k]:
            if score <= 0:
                break
            results.append({
                "id": self._ids[idx],
                "text": self._texts[idx],
                "score": round(float(score), 2),
            })
        return results


# 单例
_retriever: Optional[Retriever] = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever
