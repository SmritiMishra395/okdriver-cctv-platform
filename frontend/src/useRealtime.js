import { useEffect, useRef } from "react";

/**
 * Opens the dashboard WebSocket and re-connects with backoff if it drops.
 * `onMessage` receives { type, payload, ts } for every server-pushed event
 * (event.new, alert.new, alert.updated, camera.status_changed).
 */
export function useRealtime(onMessage) {
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  useEffect(() => {
    let socket;
    let retryTimer;
    let closedByClient = false;

    function connect() {
      const token = localStorage.getItem("okdriver_token");
      if (!token) return;
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${protocol}://${window.location.host}/ws?token=${encodeURIComponent(token)}`);

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handlerRef.current?.(data);
        } catch {
          // ignore malformed frames
        }
      };

      socket.onclose = () => {
        if (!closedByClient) {
          retryTimer = setTimeout(connect, 3000);
        }
      };
    }

    connect();
    return () => {
      closedByClient = true;
      clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);
}
