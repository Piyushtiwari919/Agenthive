import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Set


class TenantEventBus:
    """
    Tenant-scoped in-process event bus for real-time SSE notifications (FR-012, Active Procedure Glow).
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, Set[asyncio.Queue[Dict[str, Any]]]] = {}

    def subscribe(self, tenant_id: str) -> asyncio.Queue[Dict[str, Any]]:
        queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=100)
        if tenant_id not in self._subscribers:
            self._subscribers[tenant_id] = set()
        self._subscribers[tenant_id].add(queue)
        return queue

    def unsubscribe(self, tenant_id: str, queue: asyncio.Queue[Dict[str, Any]]) -> None:
        if tenant_id in self._subscribers:
            self._subscribers[tenant_id].discard(queue)
            if not self._subscribers[tenant_id]:
                del self._subscribers[tenant_id]

    def publish(self, tenant_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        event = {
            "event_type": event_type,
            "tenant_id": tenant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        queues: List[asyncio.Queue[Dict[str, Any]]] = list(self._subscribers.get(tenant_id, set()))
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    pass


tenant_event_bus = TenantEventBus()