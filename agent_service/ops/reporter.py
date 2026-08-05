"""事故报告 — LLM 把事故全流程整理成 Markdown 报告

报告内容:
  发生了什么 (事件)
  诊断证据链 (查了哪些工具, 结果)
  根因分析 (为什么)
  处理过程 (决策 + 执行 + 审批)
  结果 (恢复/未恢复)

这是 LLM 真正擅长的部分: 把零散的工具结果组织成人类可读的事故报告.
"""

import os
import time
from pathlib import Path

import config

from llm_client import chat

REPORTS_DIR = Path(__file__).parent / "incidents"


class Reporter:
    """事故报告生成器"""

    def __init__(self, reports_dir: Path = None):
        self._dir = reports_dir or REPORTS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def generate(self, incident) -> str:
        """根据事故数据生成 Markdown 报告, 返回报告文本"""
        # 事故详情
        data = incident.to_dict()
        evidence_text = "\n".join(
            f"- `{e['tool']}`: {e['result']}" for e in data["evidence"]
        ) or "- 无证据"

        # 让 LLM 组织报告
        prompt = f"""你是一名 SRE 工程师。根据以下事故信息, 生成一份事故报告。

## 事故信息
- 事故ID: {data['id']}
- 服务: {data['service']}
- 事件: {data['event_type']}
- 等级: {data['level']}
- 状态: {data['status']}
- 事件次数: {data['event_count']}
- 详情: {data['detail']}

## 诊断证据链
{evidence_text}

## 处理决策
{data['decision'] or '未记录'}

请生成 Markdown 格式的事故报告, 包含:
1. 事故概述 (发生了什么)
2. 时间线 (从发现到处理)
3. 根因分析 (结合证据推测)
4. 处理过程 (决策和审批)
5. 改进建议 (如何避免复发)
"""
        reply, _ = chat([
            {"role": "system", "content": "你是 SRE 工程师, 负责生成事故复盘报告."},
            {"role": "user", "content": prompt},
        ])

        # 组织最终报告
        report = f"""# 事故报告 {data['id']}

**服务**: {data['service']} | **等级**: {data['level']} | **状态**: {data['status']}

## 证据链
{evidence_text}

## AI 分析
{reply}

---
*报告生成: {time.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        # 存档
        path = self._dir / f"{data['id']}-report.md"
        with open(path, "w") as f:
            f.write(report)
        return report
