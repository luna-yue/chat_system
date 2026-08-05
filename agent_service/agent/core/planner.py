"""Planner — 分层决策 + 执行

第一层: switch case 规则引擎处理常见事件 (0 token)
  规则命中 → 通过工具注册表真正执行 → 结果存入诊断状态

第二层: 连续 N 个事件规则都命中不了 → 升级 LLM 兜底

第三层: LLM 决策 (低频, 只在规则覆盖不了时调用)
"""

from agent.monitor.config import PLANNER


class Planner:
    def __init__(self, bus, rules=None, llm_decision_fn=None, tool_executor=None):
        self.bus = bus
        # 规则表: (事件type, 服务) → (工具名, 参数)
        self.rules = rules or {}
        # LLM 兜底函数 (外部注入, 保持 core 与 LLM 解耦)
        self.llm_decision_fn = llm_decision_fn
        # 工具执行器 (外部注入 tool_registry.execute, 保持 core 与 monitor 解耦)
        self.tool_executor = tool_executor
        self.state = {}          # 累积诊断状态 {service: [事件...]}
        self.tool_results = {}   # 工具执行结果 {service: [结果...]}
        self.unhandled = 0       # 连续未命中规则的计数
        self.rounds = 0          # 总轮数

    def on_event(self, event: dict) -> str:
        """处理一个事件: 规则执行 → 计数 → LLM 兜底"""
        self.rounds += 1
        svc = event.get("service", "?")
        etype = event.get("type", "?")

        # 累积状态
        self.state.setdefault(svc, []).append(etype)

        # ── 第一层: 规则引擎 ──
        action = self._match_rule(etype, svc)
        if action:
            self.unhandled = 0  # 规则命中, 重置计数器
            # 支持单个 (tool, args) 或多个 [(tool, args), ...] 的链式诊断
            steps = action if isinstance(action, list) else [action]
            results = []
            for tool_name, tool_args in steps:
                if self.tool_executor:
                    result = self.tool_executor(tool_name, tool_args)
                    self.tool_results.setdefault(svc, []).append(
                        {"tool": tool_name, "result": result})
                    results.append(f"{tool_name}({tool_args}) = {result[:60]}")
                else:
                    results.append(f"{tool_name}({tool_args})")
            return f"[规则] {svc} {etype} → " + " | ".join(results)

        # ── 第二层: 计数, 未收敛才升级 ──
        self.unhandled += 1
        if self.unhandled < PLANNER["llm_threshold"]:
            return f"[等待] {svc} {etype} 规则未命中, 继续观察 (unhandled={self.unhandled})"

        # ── 第三层: LLM 兜底 ──
        # 按服务逐个处理累积的故障, 避免 LLM 只专注一个服务
        self.unhandled = 0
        if self.llm_decision_fn:
            affected = list(self.state.keys())
            decisions = []
            for svc in affected:
                svc_event = {
                    "type": self.state[svc][-1] if self.state[svc] else etype,
                    "service": svc,
                    "detail": f"累积事件: {self.state[svc]}",
                }
                decision = self.llm_decision_fn(self.state, svc_event, self.tool_results)
                decisions.append(f"{svc}: {decision}")
            return "[LLM] " + " | ".join(decisions)

        return f"[无法处理] {svc} {etype}"

    def _match_rule(self, etype: str, svc: str):
        """switch case 规则匹配, 命中返回 (tool, args), 未命中返回 None"""
        return self.rules.get((etype, svc))

    def should_converge(self) -> bool:
        """轮数上限或状态稳定 → 收敛"""
        return self.rounds >= PLANNER["max_rounds"]
