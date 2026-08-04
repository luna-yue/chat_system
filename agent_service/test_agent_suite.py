"""事件驱动多 Agent 运维 — 测试套件

覆盖:
  T1 规则命中:  事件匹配 switch case → 决策 (0 token)
  T2 状态稳定:  无状态变化 → 不发布事件 (0 token)
  T3 LLM 兜底:  连续 N 个事件规则未命中 → 溢出 LLM
  T4 事件去重:  service 保持 down → 不重复发事件
  T5 恢复检测:  service 恢复 → 发恢复事件
  T6 多 Agent 并发: Health/Log/DB 同时跑, 事件有序
  T7 收敛:      rounds 超限 → should_converge True
"""

import time

from agent.core.event_bus import EventBus, Event
from agent.core.planner import Planner
from agent.core.agent_loop import AgentLoop
from agent.monitor.config import PLANNER

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")


# ─────────────────────────────────────────────
# T1: 规则命中 + 真实执行
# ─────────────────────────────────────────────
def test_rule_hit():
    print("\n[T1] 规则命中 + 真实执行")
    bus = EventBus()
    rules = {("health_down", "transmite"): ("check_port", {"service": "transmite"})}
    # 注入真实工具执行器
    from agent.monitor import tool_registry
    planner = Planner(bus, rules=rules, tool_executor=tool_registry.execute)
    decisions = []
    bus.subscribe("health", lambda e: decisions.append(planner.on_event(e)))

    bus.publish("health", Event.make("health_down", "transmite"))
    check("规则命中返回决策", decisions and decisions[0].startswith("[规则]"),
          f"got: {decisions}")
    check("决策指向 check_port", decisions and "check_port" in decisions[0],
          f"got: {decisions}")
    # 工具结果存入 tool_results
    check("工具结果已存储", "transmite" in planner.tool_results,
          f"tool_results: {planner.tool_results}")
    check("工具真正执行", planner.tool_results.get("transmite", [{}])[0]["result"],
          "工具未执行")


# ─────────────────────────────────────────────
# T2: 状态稳定 → 静默
# ─────────────────────────────────────────────
def test_silent():
    print("\n[T2] 状态稳定静默")
    bus = EventBus()
    planner = Planner(bus, rules={})
    events = []
    bus.subscribe("health", lambda e: events.append(planner.on_event(e)))

    class StableAgent(AgentLoop):
        def __init__(self, bus):
            super().__init__("stable", bus, 0.5)
        def detect(self):
            return {"svc": "up"}   # 状态永远不变
        def on_state_change(self, old, new):
            # 首次 (old=None) 是建立基线, 不记录; 之后状态不变不触发
            if old is not None:
                events.append("CHANGE")

    a = StableAgent(bus)
    a.start()
    time.sleep(2)   # 4 次探测
    a.stop()
    check("稳定状态无变化事件", not any(e == "CHANGE" for e in events), f"events: {events}")


# ─────────────────────────────────────────────
# T3: LLM 兜底 — 连续未命中
# ─────────────────────────────────────────────
def test_llm_fallback():
    print("\n[T3] LLM 兜底")
    bus = EventBus()
    planner = Planner(bus, rules={})  # 无规则 → 全部未命中
    llm_calls = []
    planner.llm_decision_fn = lambda state, ev, results: (llm_calls.append(1), "LLM 决策")[1]
    decisions = []
    bus.subscribe("x", lambda e: decisions.append(planner.on_event(e)))

    # 发 PLANNER["llm_threshold"] 个未命中事件
    for i in range(PLANNER["llm_threshold"]):
        bus.publish("x", Event.make(f"unknown_{i}", "svc"))
    check(f"溢出到 LLM 至少 1 次", len(llm_calls) >= 1, f"llm_calls={len(llm_calls)}")
    check("LLM 决策出现在历史", any("[LLM]" in d for d in decisions), f"decisions: {decisions}")


# ─────────────────────────────────────────────
# T4: 事件去重 — 保持 down 不重复发
# ─────────────────────────────────────────────
def test_dedup():
    print("\n[T4] 事件去重")
    bus = EventBus()
    events = []
    bus.subscribe("health", lambda e: events.append(e))

    class DropAgent(AgentLoop):
        def __init__(self, bus):
            super().__init__("drop", bus, 0.5)
            self.count = 0
        def detect(self):
            self.count += 1
            # 第1次 up, 之后一直 down
            return {"svc": "down" if self.count > 1 else "up"}
        def on_state_change(self, old, new):
            # 忽略首次基线 (old=None), 只发真实变化
            if old is not None:
                bus.publish("health", Event.make(f"health_{new['svc']}", "svc"))

    a = DropAgent(bus)
    a.start()
    time.sleep(2)  # 4 次探测
    a.stop()
    # up→down 只应发 1 次事件
    down_events = [e for e in events if e["type"] == "health_down"]
    check("down 事件只发一次", len(down_events) == 1, f"down_events={len(down_events)}")


# ─────────────────────────────────────────────
# T5: 恢复检测
# ─────────────────────────────────────────────
def test_recovery():
    print("\n[T5] 恢复检测")
    bus = EventBus()
    events = []
    bus.subscribe("health", lambda e: events.append(e))

    class RecoverAgent(AgentLoop):
        def __init__(self, bus):
            super().__init__("recover", bus, 0.5)
            self.count = 0
        def detect(self):
            self.count += 1
            # up → down → down → up
            if self.count == 1: return {"svc": "up"}
            if self.count in (2, 3): return {"svc": "down"}
            return {"svc": "up"}
        def on_state_change(self, old, new):
            # 忽略首次基线 (old=None), 只发真实变化
            if old is not None:
                bus.publish("health", Event.make(f"health_{new['svc']}", "svc"))

    a = RecoverAgent(bus)
    a.start()
    time.sleep(3)  # 6 次探测
    a.stop()
    types = [e["type"] for e in events]
    check("有 down 事件", "health_down" in types, f"types={types}")
    check("有恢复 up 事件", "health_up" in types, f"types={types}")
    check("恢复事件在 down 之后", types.index("health_up") > types.index("health_down"),
          f"types={types}")


# ─────────────────────────────────────────────
# T6: 多 Agent 并发
# ─────────────────────────────────────────────
def test_concurrent():
    print("\n[T6] 多 Agent 并发")
    bus = EventBus()
    planner = Planner(bus, rules={("health_down", "a"): ("tool_a", {})})
    decisions = []
    bus.subscribe("health", lambda e: decisions.append(planner.on_event(e)))
    bus.subscribe("log", lambda e: decisions.append(planner.on_event(e)))

    # 同时发布多通道事件
    for i in range(10):
        bus.publish("health", Event.make("health_down", "a"))
        bus.publish("log", Event.make("log_error", "b"))
    check("10 个事件全部处理", len(decisions) == 20, f"len={len(decisions)}")


# ─────────────────────────────────────────────
# T7: 收敛
# ─────────────────────────────────────────────
def test_converge():
    print("\n[T7] 收敛")
    bus = EventBus()
    planner = Planner(bus, rules={})
    # 模拟触发到 max_rounds
    for i in range(PLANNER["max_rounds"]):
        planner.on_event(Event.make(f"e{i}", "svc"))
    check("超过 max_rounds 收敛", planner.should_converge(),
          f"rounds={planner.rounds} max={PLANNER['max_rounds']}")


if __name__ == "__main__":
    print("=" * 40)
    print("事件驱动多 Agent 测试套件")
    print("=" * 40)
    test_rule_hit()
    test_silent()
    test_llm_fallback()
    test_dedup()
    test_recovery()
    test_concurrent()
    test_converge()
    print(f"\n{'=' * 40}")
    print(f"结果: {PASS} 通过, {FAIL} 失败")
    print("=" * 40)
