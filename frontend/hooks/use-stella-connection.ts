'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { stellaWS, createWSMessage, ConnectionStatus, StellaWSMessage, StellaWSResponse } from '@/lib/websocket';

export interface UseStellaConnectionReturn {
  status: ConnectionStatus;
  isConnected: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  send: (message: StellaWSMessage) => void;
  request: <T = any>(endpoint: string, payload?: any, timeoutMs?: number) => Promise<T>;
  onMessage: (listener: (msg: StellaWSResponse) => void) => () => void;
  lastConnectedAt: string | null;
  lastDisconnectedAt: string | null;
}

const CONNECTION_STATUS_KEY = 'stella_connection_status';
const LAST_CONNECTED_KEY = 'stella_last_connected_at';
const LAST_DISCONNECTED_KEY = 'stella_last_disconnected_at';

export function useStellaConnection(): UseStellaConnectionReturn {
  const [status, setStatus] = useState<ConnectionStatus>(() => {
    try {
      const saved = localStorage.getItem(CONNECTION_STATUS_KEY);
      return (saved as ConnectionStatus) || 'disconnected';
    } catch { return 'disconnected'; }
  });

  const [lastConnectedAt, setLastConnectedAt] = useState<string | null>(() => {
    try { return localStorage.getItem(LAST_CONNECTED_KEY); } catch { return null; }
  });

  const [lastDisconnectedAt, setLastDisconnectedAt] = useState<string | null>(() => {
    try { return localStorage.getItem(LAST_DISCONNECTED_KEY); } catch { return null; }
  });

  const listenersRef = useRef<Map<string, (msg: StellaWSResponse) => void>>(new Map());

  // Persist status changes to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(CONNECTION_STATUS_KEY, status);
      if (status === 'connected') {
        setLastConnectedAt(new Date().toISOString());
        localStorage.setItem(LAST_CONNECTED_KEY, lastConnectedAt || new Date().toISOString());
      } else if (status === 'disconnected') {
        setLastDisconnectedAt(new Date().toISOString());
        localStorage.setItem(LAST_DISCONNECTED_KEY, lastDisconnectedAt || new Date().toISOString());
      }
    } catch { /* localStorage may be unavailable */ }
  }, [status, lastConnectedAt, lastDisconnectedAt]);

  // Sync manager status to React state
  useEffect(() => {
    const unsub = stellaWS.onStatusChange((newStatus) => {
      setStatus(newStatus);
      const now = new Date().toISOString();
      try {
        localStorage.setItem(CONNECTION_STATUS_KEY, newStatus);
        if (newStatus === 'connected') {
          localStorage.setItem(LAST_CONNECTED_KEY, now);
          setLastConnectedAt(now);
        } else if (newStatus === 'disconnected') {
          localStorage.setItem(LAST_DISCONNECTED_KEY, now);
          setLastDisconnectedAt(now);
        }
      } catch { /* ignore */ }
    });
    return unsub;
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    stellaWS.connect().catch(() => {
      // Connection failures are handled by the manager's reconnection logic
    });
    return () => {
      // Note: we don't disconnect on unmount so the connection persists across route changes
      // Uncomment the line below if you want to close the connection on unmount:
      // stellaWS.disconnect();
    };
  }, []);

  const send = useCallback((message: StellaWSMessage) => {
    stellaWS.send(message);
  }, []);

  const request = useCallback(async <T = any>(endpoint: string, payload?: any, timeoutMs?: number): Promise<T> => {
    const msg = createWSMessage(endpoint, payload);
    const result = await stellaWS.request(msg, timeoutMs);
    return result as T;
  }, []);

  const onMessage = useCallback((listener: (msg: StellaWSResponse) => void) => {
    const key = Math.random().toString(36).slice(2, 9);
    const unsub = stellaWS.onMessage((msg) => listener(msg));
    listenersRef.current.set(key, listener);
    return unsub;
  }, []);

  return {
    status,
    isConnected: status === 'connected',
    connect: () => stellaWS.connect(),
    disconnect: () => stellaWS.disconnect(),
    send,
    request,
    onMessage,
    lastConnectedAt,
    lastDisconnectedAt,
  };
}