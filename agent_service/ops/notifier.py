"""告警通知 — 把事故/审批推送给运维

支持:
  1. 文件通知 (写 alerts.log, 最简单)
  2. Webhook 通知 (企业微信/飞书/自定义 URL, 可扩展)

真实项目参考: ITOps Agent 推送企微/钉钉, RunbookHermes 多入口.
"""

import os
import time
from pathlib import Path

ALERTS_LOG = Path(__file__).parent / "alerts.log"

# Webhook URL (可通过环境变量配置, 不硬编码)
WEBHOOK_URL = os.getenv("OPS_WEBHOOK_URL", "")


class Notifier:
    """告警通知器"""

    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url or WEBHOOK_URL
        self.alerts_log = ALERTS_LOG

    def alert(self, level: str, message: str):
        """发一条告警"""
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        line = f"[{ts}] [{level}] {message}"
        print(f"[notifier] {line}")
        # 写文件
        with open(self.alerts_log, "a") as f:
            f.write(line + "\n")
        # Webhook (如果配置了)
        if self.webhook_url:
            self._webhook(level, message)

    def incident_created(self, incident):
        """新事故通知"""
        self.alert(incident.level,
                   f"新事故 {incident.id}: {incident.service} {incident.event_type}")

    def approval_pending(self, req):
        """待审批通知"""
        self.alert("warning",
                   f"待审批 {req.id}: {req.service} → {req.action} (风险:{req.risk})")

    def incident_resolved(self, incident):
        """事故恢复通知"""
        self.alert("info", f"事故已恢复 {incident.id}: {incident.service}")

    def _webhook(self, level: str, message: str):
        """发送 Webhook (企业微信/飞书格式可扩展)"""
        import urllib.request
        payload = f'{{"level":"{level}","message":"{message}"}}'
        try:
            req = urllib.request.Request(
                self.webhook_url, data=payload.encode(),
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=3)
        except Exception as e:
            print(f"[notifier] webhook 失败: {e}")
