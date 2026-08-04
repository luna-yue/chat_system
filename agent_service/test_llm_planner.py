"""真实 LLM 兜底测试:
事件规则未命中 → 连续触发 → 升级到 DeepSeek 决策
"""
import os

os.environ.setdefault("DEEPSEEK_API_KEY", "your-api-key-here")

from agent.core.event_bus import EventBus, Event
from agent.core.planner import Planner
from agent.monitor import llm_planner
from agent.monitor.config import PLANNER

# 规则表故意留空, 让所有事件都未命中 → 走 LLM
RULES = {}

bus = EventBus()
planner = Planner(bus, rules=RULES, llm_decision_fn=llm_planner.decide)

print("=== 模拟复杂事件: transmite down + message down + redis 连接高 ===\n")
# 发几个规则覆盖不了的关联事件
events = [
    Event.make("health_down", "transmite", "port 10004 down", "critical"),
    Event.make("health_down", "message", "port 10005 down", "critical"),
    Event.make("db_high", "redis", "connections: 200", "warning"),
]

decisions = []
for i, e in enumerate(events):
    d = planner.on_event(e)
    decisions.append(d)
    print(f"事件{i+1}: {e['type']}/{e['service']} → {d}")
    print()

print("\n=== 结果 ===")
llm_decisions = [d for d in decisions if d.startswith("[LLM]")]
print(f"共 {len(decisions)} 个事件, {len(llm_decisions)} 次走了 LLM")
for d in llm_decisions:
    print(f"  {d[:200]}")
