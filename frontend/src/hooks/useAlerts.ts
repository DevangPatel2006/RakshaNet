import { useState, useEffect, useRef } from 'react';
import type { Alert } from '../types';

export function useAlerts(token: string | null) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    setAlerts([]); // Reset alerts when token changes
    if (!token) {
      setWsConnected(false);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    const wsUrl = `ws://localhost:8000/alerts/stream?token=${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setWsConnected(true);
      console.log("WebSocket connected successfully.");
    };

    ws.onmessage = (event) => {
      try {
        const alertData: Alert = JSON.parse(event.data);
        console.log("WebSocket Alert Received:", alertData);
        setAlerts(prev => [alertData, ...prev]);
      } catch (err) {
        console.error("Error parsing WebSocket alert payload:", err);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
      console.log("WebSocket closed.");
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      setWsConnected(false);
    };

    wsRef.current = ws;

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [token]);

  return { alerts, setAlerts, wsConnected };
}
export default useAlerts;
