"""HITL 审批 — 高风险操作必须人工确认 (人在环路)

企业级运维的铁律: 高风险动作 (重启/扩缩容/清理) 不能由 AI 直接执行,
必须:
  1. Agent 生成"建议 + 证据链"
  2. 放入 pending 审批队列
  3. 人工确认 (approve) 才执行
  4. 人工拒绝 (reject) 则跳过

对应真实项目: RunbookHermes 的 approval-gated remediation,
ITOps Agent 的手机审批, Auto-SRE 的语音授权.
"""

import json
import time
from pathlib import Path

# 审批记录目录
APPROVALS_DIR = Path(__file__).parent / "incidents"


class ApprovalRequest:
    """一个待审批的高风险操作"""

    def __init__(self, incident_id, service, action, evidence, risk):
        self.id = f"APR-{int(time.time())}-{service}"
        self.incident_id = incident_id
        self.service = service
        self.action = action          # 要执行的操作 (如 restart_service)
        self.evidence = evidence      # 证据链 (为什么需要这个操作)
        self.risk = risk              # 风险等级 (medium/high)
        self.status = "PENDING"       # PENDING → APPROVED / REJECTED
        self.created_at = time.time()

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "service": self.service,
            "action": self.action,
            "evidence": self.evidence,
            "risk": self.risk,
            "status": self.status,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created_at)),
        }


class ApprovalManager:
    """审批管理器 — pending 队列 + 确认/拒绝"""

    def __init__(self, approvals_dir: Path = None):
        self._dir = approvals_dir or APPROVALS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._pending = {}    # approval_id → ApprovalRequest

    def request(self, incident_id, service, action, evidence, risk="medium") -> ApprovalRequest:
        """高危操作 → 生成审批请求, 进入 pending"""
        req = ApprovalRequest(incident_id, service, action, evidence, risk)
        self._pending[req.id] = req
        print(f"[approval] ⚠️ 高危操作待审批: {req.id} {service} → {action} (风险:{risk})")
        print(f"[approval]   证据: {evidence}")
        return req

    def approve(self, approval_id: str) -> ApprovalRequest:
        """人工确认 → 返回审批请求, 由调用方执行 action"""
        req = self._pending.get(approval_id)
        if not req:
            return None
        req.status = "APPROVED"
        self._save(req)
        print(f"[approval] ✅ 已审批: {approval_id}, 可以执行 {req.action}")
        return req

    def reject(self, approval_id: str) -> ApprovalRequest:
        """人工拒绝"""
        req = self._pending.get(approval_id)
        if not req:
            return None
        req.status = "REJECTED"
        self._pending.pop(approval_id)
        self._save(req)
        print(f"[approval] ❌ 已拒绝: {approval_id}, 跳过 {req.action}")
        return req

    def pending_requests(self) -> list:
        """所有待审批的操作"""
        return list(self._pending.values())

    def _save(self, req: ApprovalRequest):
        path = self._dir / f"{req.id}.json"
        with open(path, "w") as f:
            json.dump(req.to_dict(), f, ensure_ascii=False, indent=2)


# ── 风险分级: 哪些操作需要审批 ──
def is_high_risk(action: str) -> bool:
    """判断操作是否高风险, 需要审批"""
    HIGH_RISK_ACTIONS = {
        "restart_service",   # 重启服务 (可能影响正在处理的消息)
        "kill_process",      # 杀进程
        "delete_log",        # 删日志
        "scale_out",         # 扩容
    }
    return action in HIGH_RISK_ACTIONS
