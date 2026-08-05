"""事故管理 — 每个故障变成一个事故, 有生命周期/去重/状态

生命周期:
  OPEN(发现) → INVESTIGATING(诊断中) → RESOLVED(已恢复) / CLOSED(已归档)

核心价值:
  1. 去重: 同一服务重复告警合并到同一个事故, 不刷屏
  2. 状态: 事故有明确生命周期, 可追踪
  3. 关联: 记录证据链, 支持事后分析
"""

import json
import os
import time
from pathlib import Path

# 事故存档目录
INCIDENTS_DIR = Path(__file__).parent / "incidents"


class Incident:
    """单个事故对象"""

    def __init__(self, incident_id, service, event_type, level, detail):
        self.id = incident_id
        self.service = service
        self.event_type = event_type
        self.level = level           # info / warning / critical
        self.status = "OPEN"         # OPEN → INVESTIGATING → RESOLVED/CLOSED
        self.created_at = time.time()
        self.updated_at = time.time()
        self.event_count = 1         # 去重: 同一事故累计事件数
        self.evidence = []           # 诊断证据链
        self.decision = ""           # 处理决策
        self.detail = detail

    def to_dict(self):
        return {
            "id": self.id,
            "service": self.service,
            "event_type": self.event_type,
            "level": self.level,
            "status": self.status,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created_at)),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.updated_at)),
            "event_count": self.event_count,
            "evidence": self.evidence[-5:],   # 最近 5 条证据
            "decision": self.decision,
            "detail": self.detail,
        }


class IncidentManager:
    """事故管理器 — 负责去重/生命周期/存档"""

    def __init__(self, incidents_dir: Path = None):
        self._dir = incidents_dir or INCIDENTS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._active = {}    # incident_id → Incident
        self._seq = 0

    def _next_id(self):
        self._seq += 1
        return f"INC-{int(time.time())}-{self._seq}"

    def on_event(self, event: dict) -> Incident:
        """收到事件, 返回对应事故 (新建或去重合并)"""
        service = event.get("service", "?")
        etype = event.get("type", "?")

        # 去重: 同一服务 + 同一类型, 若已有 OPEN 事故则合并
        for inc in self._active.values():
            if (inc.service == service and inc.event_type == etype
                    and inc.status in ("OPEN", "INVESTIGATING")):
                inc.event_count += 1
                inc.updated_at = time.time()
                inc.detail = event.get("detail", inc.detail)
                return inc

        # 新建事故
        inc = Incident(
            self._next_id(), service, etype,
            event.get("level", "warning"), event.get("detail", ""),
        )
        self._active[inc.id] = inc
        print(f"[incident] 新建事故 {inc.id}: {service} {etype} ({inc.level})")
        return inc

    def add_evidence(self, incident_id: str, tool: str, result: str):
        """记录诊断证据"""
        inc = self._active.get(incident_id)
        if inc:
            inc.evidence.append({"tool": tool, "result": result[:100], "ts": time.time()})
            inc.updated_at = time.time()

    def set_decision(self, incident_id: str, decision: str):
        """记录处理决策"""
        inc = self._active.get(incident_id)
        if inc:
            inc.decision = decision
            inc.updated_at = time.time()

    def resolve(self, incident_id: str, note: str = ""):
        """事故已恢复"""
        inc = self._active.get(incident_id)
        if inc:
            inc.status = "RESOLVED"
            inc.decision += f" | 已恢复: {note}"
            inc.updated_at = time.time()

    def close(self, incident_id: str):
        """事故归档 (从活跃列表移除, 写盘)"""
        inc = self._active.pop(incident_id, None)
        if inc:
            inc.status = "CLOSED"
            self._save(inc)
            return inc
        return None

    def _save(self, inc: Incident):
        """把事故存为 JSON 档案"""
        path = self._dir / f"{inc.id}.json"
        with open(path, "w") as f:
            json.dump(inc.to_dict(), f, ensure_ascii=False, indent=2)

    def active_incidents(self):
        """当前未归档的事故"""
        return list(self._active.values())

    def summary(self) -> str:
        """活跃事故摘要"""
        if not self._active:
            return "当前无活跃事故"
        lines = ["活跃事故:"]
        for inc in self._active.values():
            lines.append(
                f"  {inc.id} [{inc.status}] {inc.service} {inc.event_type} "
                f"({inc.level}, 事件×{inc.event_count})"
            )
        return "\n".join(lines)
