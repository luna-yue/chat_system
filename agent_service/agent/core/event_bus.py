"""事件总线 — 发布/订阅解耦

Agent 之间不直接通信, 只通过事件总线发布/订阅.
后续可替换为 Redis pub/sub 实现跨进程, 接口不变.
"""

import json
import queue
import threading
import time
from collections import defaultdict


class EventBus:
    """内存事件总线 (单进程). 接口与 Redis pub/sub 对齐:
    publish(channel, event)  → Redis: redis.publish(channel, json)
    subscribe(channel, cb)   → Redis: redis.subscribe(channel, handler)
    """

    def __init__(self):
        self._subscribers = defaultdict(list)  # channel → [callback]
        self._lock = threading.Lock()

    def publish(self, channel: str, event: dict) -> None:
        """向 channel 发布事件, 同步调用所有订阅者"""
        event["_ts"] = time.time()
        with self._lock:
            subs = list(self._subscribers.get(channel, []))
        for cb in subs:
            try:
                cb(event)
            except Exception as e:
                print(f"[EventBus] 订阅者异常: {e}")

    def subscribe(self, channel: str, callback) -> None:
        """订阅 channel, 事件到达时回调"""
        with self._lock:
            self._subscribers[channel].append(callback)

    def unsubscribe(self, channel: str, callback) -> None:
        with self._lock:
            if callback in self._subscribers[channel]:
                self._subscribers[channel].remove(callback)


class Event:
    """事件格式约定 — Agent 之间传递的唯一结构"""
    # type:   事件类型 (health_down/log_error/db_high...)
    # service: 涉及的服务名
    # detail:  详情 (JSON 字符串)
    # level:   info/warning/critical
    @staticmethod
    def make(etype: str, service: str, detail: str = "", level: str = "warning") -> dict:
        return {
            "type": etype,
            "service": service,
            "detail": detail,
            "level": level,
        }
