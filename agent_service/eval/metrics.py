"""Agent 评估脚本 — 量化指标: 工具准确率、延迟、成功率

用法:
  cd agent_service && DEEPSEEK_API_KEY="sk-xxx" python3 eval/metrics.py
"""

import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.react_loop import run_with_trace

EVAL_FILE = Path(__file__).parent / "test_set.json"


def load_test_set():
    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate():
    cases = load_test_set()
    total = len(cases)
    tool_correct = 0
    tool_wrong = 0
    tool_not_called = 0
    errors = 0
    latencies = []

    print(f"Running {total} test cases...")
    for i, case in enumerate(cases):
        qid = case["id"]
        question = case["question"]
        expected = case.get("expected_tool")  # None for chitchat

        t0 = time.time()
        try:
            result = run_with_trace("test_user", question)
            reply = result.reply
            tool_used = result.tools_called[0] if result.tools_called else None
        except Exception as e:
            errors += 1
            print(f"  [{qid}] ERROR: {e}")
            continue
        elapsed = (time.time() - t0) * 1000
        latencies.append(elapsed)

        if expected is None:
            continue  # chitchat - skip accuracy
        elif tool_used == expected:
            tool_correct += 1
        elif tool_used is None:
            tool_not_called += 1
            if tool_not_called <= 5:
                print(f"  [{qid}] MISS: '{question[:40]}' exp={expected}")
        else:
            tool_wrong += 1
            if tool_wrong <= 5:
                print(f"  [{qid}] WRONG: '{question[:40]}' exp={expected} got={tool_used}")

        if (i + 1) % 50 == 0:
            print(f"  ... {i+1}/{total}")

    # Stats
    tool_total = tool_correct + tool_wrong + tool_not_called
    accuracy = tool_correct / tool_total * 100 if tool_total > 0 else 0
    avg_lat = sum(latencies) / len(latencies) if latencies else 0
    p50 = sorted(latencies)[len(latencies) // 2] if latencies else 0
    p95 = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    print(f"\n{'='*50}")
    print(f"  测试集: {total} 条")
    print(f"  工具准确率: {tool_correct}/{tool_total} ({accuracy:.1f}%)")
    print(f"  未调用: {tool_not_called}  调错: {tool_wrong}  异常: {errors}")
    print(f"  平均延迟: {avg_lat:.0f}ms  P50: {p50:.0f}ms  P95: {p95:.0f}ms")
    print(f"{'='*50}")


if __name__ == "__main__":
    evaluate()
