"""完整推理链展示 — 打印 LLM 每一步的工具调用和最终结论

目的: 让你看到 Agent 是怎么一步步"思考"的, 不只是结论
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config

from agent.core.event_bus import Event, EventBus
from agent.core.planner import Planner
from agent.monitor import tool_registry, llm_planner
from llm_client import chat_with_tools


def trace_scene(name, events):
    """驱动 LLM 完整推理, 打印每一步"""
    print("\n" + "=" * 60)
    print(f"场景: {name}")
    print("=" * 60)

    # 构造诊断状态 + 事件
    state = {}
    for ev in events:
        svc = ev.get("service")
        state.setdefault(svc, []).append(ev.get("type"))

    event = events[-1]
    tool_results = {}

    # 手动驱动 LLM 决策循环 (和 decide 一样, 但打印更多)
    messages = [
        {"role": "system", "content": llm_planner.SYSTEM_PROMPT},
        {"role": "user", "content":
            f"## 诊断状态\n{state}\n\n## 新事件\n{event}\n\n请诊断"},
    ]

    round_no = 0
    while round_no < 5:
        reply = chat_with_tools(messages, llm_planner.FALLBACK_TOOLS)

        if reply.get("tool_calls"):
            messages.append(reply["message"])
            for tc in reply["tool_calls"]:
                name = tc["function"]["name"]
                args = tc["function"].get("arguments", {})
                result = tool_registry.execute(name, args)
                print(f"  ▶ 第{round_no+1}轮: 调 {name}({args})")
                print(f"    → {result[:100]}")
                messages.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": result})
            round_no += 1
            continue

        # 最终结论
        print(f"\n  🏁 第{round_no+1}轮: LLM 结论:")
        print(f"    {reply.get('content', '')[:400]}")
        return

    print("\n  🏁 轮数耗尽, 无法自动诊断")


def main():
    # 场景 B: 信息矛盾 (端口通+进程活, 但上报 down) — 最能展示推理
    trace_scene("信息矛盾: transmite 上报 down, 但实际端口通+进程活", [
        Event.make("health_down", "transmite", "business unavailable", "critical"),
        Event.make("health_down", "transmite", "business unavailable", "critical"),
    ])


if __name__ == "__main__":
    main()
