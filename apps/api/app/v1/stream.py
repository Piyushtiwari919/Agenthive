import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from app.core.events import tenant_event_bus
from app.core.security import resolve_tenant_scope
from app.domain.tenant import TenantScope

router = APIRouter(prefix="/events", tags=["Real-Time Activity Stream (SSE)"])


@router.get("/stream")
async def stream_tenant_events(
    max_events: int = Query(default=0, ge=0, le=100),
    scope: TenantScope = Depends(resolve_tenant_scope),
) -> EventSourceResponse:
    """
    Tenant-scoped Server-Sent Events (SSE) endpoint delivering <5s task status updates,
    handoff notifications, and active procedure execution glow events (FR-012).
    """

    async def event_generator() -> AsyncGenerator[dict, None]:
        queue = tenant_event_bus.subscribe(scope.tenant_id)
        emitted = 0
        try:
            yield {
                "event": "connected",
                "data": json.dumps({"tenant_id": scope.tenant_id, "status": "subscribed"}),
            }
            while True:
                if max_events > 0 and emitted >= max_events:
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    emitted += 1
                    yield {
                        "event": event["event_type"],
                        "data": json.dumps(event),
                    }
                except asyncio.TimeoutError:
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"tenant_id": scope.tenant_id}),
                    }
                    if max_events > 0:
                        break
        finally:
            tenant_event_bus.unsubscribe(scope.tenant_id, queue)

    return EventSourceResponse(event_generator())