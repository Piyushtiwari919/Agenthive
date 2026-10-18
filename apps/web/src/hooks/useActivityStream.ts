import { useEffect, useState } from "react";
import { API_BASE_URL } from "../api/client";

export interface LiveActivityEvent {
  event_type: string;
  tenant_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

export function useActivityStream(
  tenantId: string,
  onActivityChange?: (evt: LiveActivityEvent) => void
) {
  const [connected, setConnected] = useState<boolean>(false);
  const [lastEvent, setLastEvent] = useState<LiveActivityEvent | null>(null);

  useEffect(() => {
    setConnected(false);
    setLastEvent(null);

    if (typeof EventSource === "undefined") {
      return;
    }

    const streamUrl = `${API_BASE_URL}/events/stream?tenant_id=${encodeURIComponent(tenantId)}`;
    const es = new EventSource(streamUrl);

    es.addEventListener("connected", () => {
      setConnected(true);
    });

    const handleEvent = (raw: MessageEvent) => {
      try {
        const parsed = JSON.parse(raw.data) as LiveActivityEvent;
        if (parsed.tenant_id === tenantId) {
          setLastEvent(parsed);
          onActivityChange?.(parsed);
        }
      } catch {
        // Ignore malformed frame
      }
    };

    es.addEventListener("procedure_activity", handleEvent);
    es.addEventListener("task_status_updated", handleEvent);
    es.addEventListener("handoff_created", handleEvent);
    es.addEventListener("handoff_status_updated", handleEvent);
    es.addEventListener("agent_registered", handleEvent);

    es.onerror = () => {
      setConnected(false);
    };

    return () => {
      es.close();
    };
  }, [tenantId]);

  return { connected, lastEvent };
}