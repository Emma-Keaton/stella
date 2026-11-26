'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { StellaCompanion, type CompanionPosition } from '@/components/companion/StellaCompanion';
import { useStellaConnection } from '@/hooks/use-stella-connection';
import { createWSMessage } from '@/lib/websocket';
import { AssistantTheme } from '@/lib/types';

const loadPosition = (): CompanionPosition => {
  try {
    const raw = localStorage.getItem('stella_companion_position');
    if (raw) {
      const p = JSON.parse(raw);
      return { x: p.x ?? 20, y: p.y ?? 20, scale: p.scale ?? 1.0 };
    }
  } catch {}
  return { x: 20, y: 20, scale: 1.0 };
};

const savePosition = (pos: CompanionPosition) => {
  try { localStorage.setItem('stella_companion_position', JSON.stringify(pos)); } catch {}
};

const loadTheme = (): AssistantTheme => {
  try {
    const t = localStorage.getItem('stella_theme');
    if (t && (t === 'void' || t === 'oled' || t === 'aurora' || t === 'light' || t === 'solar')) return t;
  } catch {}
  return 'void';
};

export default function CompanionPage() {
  const { isConnected: wsConnected, send, onMessage } = useStellaConnection();
  const [theme, setTheme] = useState<AssistantTheme>(loadTheme());
  const [clickThrough, setClickThrough] = useState(false);
  const [position, setPosition] = useState<CompanionPosition>(loadPosition());
  const [expression, setExpression] = useState<'idle' | 'listening' | 'thinking' | 'talking' | 'success' | 'error'>('idle');

  useEffect(() => {
    const t = loadTheme();
    if (t !== theme) setTheme(t);
  }, [theme]);

  useEffect(() => {
    const unsub = onMessage((msg) => {
      if (msg.endpoint === 'companion.expression' && msg.result?.expression) {
        setExpression(msg.result.expression);
      }
      if (msg.endpoint === 'companion.click-through' && typeof msg.result?.enabled === 'boolean') {
        setClickThrough(msg.result.enabled);
      }
    });
    return () => unsub();
  }, [onMessage]);

  const onPositionChange = useCallback((pos: CompanionPosition) => {
    setPosition(pos);
    savePosition(pos);
    if (wsConnected) {
      send(createWSMessage('companion.position', {
        x: pos.x, y: pos.y, scale: pos.scale, ts: Date.now(),
      }));
    }
  }, [wsConnected, send]);

  return (
    <div
      style={{
        width: '100vw', height: '100vh',
        background: 'transparent',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <StellaCompanion
        initialPosition={position}
        theme={theme}
        clickThrough={clickThrough}
        onPositionChange={onPositionChange}
        onExpressionChange={() => {}}
      />
    </div>
  );
}