"use client";

import { useEffect, useRef, useState } from "react";
import { WS_URL } from "./api";
import type { LiveTick } from "./types";

/**
 * Subscribes to /ws/live and keeps the most recent tick per machine.
 * Reconnects with backoff on drop -- a dashboard that silently stops
 * updating after one dropped connection is worse than one that never
 * connected in the first place.
 */
export function useLiveFeed() {
  const [ticksByMachine, setTicksByMachine] = useState<Record<number, LiveTick>>({});
  const [connected, setConnected] = useState(false);
  const retryDelay = useRef(1000);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    function connect() {
      socket = new WebSocket(WS_URL);

      socket.onopen = () => {
        setConnected(true);
        retryDelay.current = 1000;
      };

      socket.onmessage = (event) => {
        const tick = JSON.parse(event.data) as LiveTick;
        setTicksByMachine((prev) => ({ ...prev, [tick.machine_id]: tick }));
      };

      socket.onclose = () => {
        setConnected(false);
        if (cancelled) return;
        retryTimer = setTimeout(connect, retryDelay.current);
        retryDelay.current = Math.min(retryDelay.current * 2, 15000);
      };

      socket.onerror = () => socket?.close();
    }

    connect();
    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  return { ticksByMachine, connected };
}
