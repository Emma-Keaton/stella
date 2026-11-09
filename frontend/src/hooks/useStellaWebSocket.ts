'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

interface UseStellaWebSocketOptions {
  token: string;
  onTranscript: (text: string, isFinal: boolean) => void;
  onResponse: (text: string) => void;
  onStatusChange: (status: 'connecting' | 'connected' | 'disconnected' | 'error') => void;
  onError: (error: Error) => void;
  onAudioResponse: (audioData: ArrayBuffer) => void;
}

interface UseStellaWebSocketReturn {
  isConnected: boolean;
  sendText: (text: string) => void;
  sendAudio: (audioData: ArrayBuffer) => void;
  sendCommand: (command: string, params?: any) => void;
  disconnect: () => void;
}

export function useStellaWebSocket({
  token,
  onTranscript,
  onResponse,
  onStatusChange,
  onError,
  onAudioResponse,
}: UseStellaWebSocketOptions): UseStellaWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!token) return;

    try {
      const wsUrl = `ws://localhost:8765/ws?token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttempts.current = 0;
        onStatusChange('connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          switch (data.type) {
            case 'transcript':
              onTranscript(data.text, data.isFinal);
              break;
            case 'response':
              onResponse(data.text);
              break;
            case 'audio':
              if (data.audioData) {
                const binaryString = atob(data.audioData);
                const bytes = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {
                  bytes[i] = binaryString.charCodeAt(i);
                }
                onAudioResponse(bytes.buffer);
              }
              break;
            case 'status':
              onStatusChange(data.status);
              break;
            case 'error':
              onError(new Error(data.message));
              break;
          }
        } catch (e) {
          console.error('WebSocket message parse error:', e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        onStatusChange('disconnected');

        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = (error) => {
        onError(new Error('WebSocket connection error'));
      };
    } catch (e) {
      onError(e as Error);
    }
  }, [token, onTranscript, onResponse, onStatusChange, onError, onAudioResponse]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendText = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'text', text }));
    }
  }, []);

  const sendAudio = useCallback((audioData: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const base64 = btoa(String.fromCharCode(...new Uint8Array(audioData)));
      wsRef.current.send(JSON.stringify({ type: 'audio', audioData: base64 }));
    }
  }, []);

  const sendCommand = useCallback((command: string, params?: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'command', command, params }));
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  return {
    isConnected,
    sendText,
    sendAudio,
    sendCommand,
    disconnect,
  };
}