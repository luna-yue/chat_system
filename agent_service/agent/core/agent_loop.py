"""Agent 循环框架 — 持续探测 + 状态变化检测

每个监控 Agent 继承此类:
  1. 周期性调用 detect() 探测目标状态 (纯代码, 0 token)
  2. 状态没变 → 静默 (不发布事件)
  3. 状态变化 → 发布事件到总线

关键设计: 状态变化检测在 Agent 层, 不经过 LLM.
只有变化才发事件, 正常状态零开销.
"""

import threading
import time


class AgentLoop:
    """通用 Agent 循环基类"""

    def __init__(self, name: str, bus, interval: float):
        """
        Args:
            name:     Agent 名
            bus:      EventBus 实例
            interval: 探测间隔 (秒)
        """
        self.name = name
        self.bus = bus
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None

    # ── 子类必须实现 ──
    def detect(self) -> dict:
        """探测目标状态, 返回当前状态快照 (纯代码, 不调 LLM)"""
        raise NotImplementedError

    def on_state_change(self, old_state: dict, new_state: dict):
        """状态变化回调, 子类决定发布什么事件"""
        raise NotImplementedError

    # ── 框架逻辑 ──
    def run_loop(self):
        """持续循环: 探测 → 比较 → 变化则回调

        首次探测也算变化 (None → 当前状态), 这样启动时就存在的
        异常 (服务 down/超时) 也会被上报, 而不是静默忽略.
        """
        last_state = None
        while not self._stop.is_set():
            try:
                new_state = self.detect()
                if new_state != last_state:
                    # 首次 (last=None) 也算变化, 让 on_state_change 决定是否上报
                    self.on_state_change(last_state, new_state)
                    last_state = new_state
            except Exception as e:
                print(f"[{self.name}] detect 异常: {e}")
            self._stop.wait(self.interval)

    def start(self):
        self._thread = threading.Thread(target=self.run_loop, daemon=True)
        self._thread.start()
        print(f"[{self.name}] 已启动, 探测间隔 {self.interval}s")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        print(f"[{self.name}] 已停止")
