"""Agent 核心引擎 — 与具体业务解耦

core/
  event_bus.py   事件总线 (发布/订阅)
  agent_loop.py  Agent 循环框架 (持续探测 + 状态变化检测)
  planner.py     Planner 决策 (规则引擎 + LLM 兜底)
"""
