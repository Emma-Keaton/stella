'use client';

import React, {
  useState, useEffect, useRef, useCallback,
} from 'react';
import { useStellaConnection } from '@/hooks/use-stella-connection';
import { createWSMessage } from '@/lib/websocket';
import { THEME_CONFIGS } from '@/lib/theme';
import { AssistantTheme } from '@/lib/types';

export type CompanionExpression =
  | 'idle' | 'listening' | 'thinking' | 'talking' | 'success' | 'error';

export interface CompanionPosition {
  x: number; y: number; scale: number;
}

interface StellaCompanionProps {
  initialPosition?: CompanionPosition;
  theme: AssistantTheme;
  clickThrough?: boolean;
  onPositionChange?: (pos: CompanionPosition) => void;
  onExpressionChange?: (expr: CompanionExpression) => void;
}

const DEFAULT_POSITION: CompanionPosition = { x: 20, y: 20, scale: 1.0 };
const DRAG_HANDLE_SIZE = 40;

const SPRITE_BY_EXPR: Record<CompanionExpression, string> = {
  idle: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><circle cx="100" cy="100" r="80" fill="%2300E5A3"/><ellipse cx="100" cy="90" rx="30" ry="20" fill="%23030509"/><circle cx="75" cy="85" r="8" fill="%23ffffff"/><circle cx="125" cy="85" r="8" fill="%23ffffff"/></svg>',
  listening: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><circle cx="100" cy="100" r="80" fill="%2300F0FF"/><ellipse cx="100" cy="90" rx="30" ry="20" fill="%23030509"/><circle cx="75" cy="85" r="8" fill="%23ffffff"/><circle cx="125" cy="85" r="8" fill="%23ffffff"/></svg>',
  thinking: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><circle cx="100" cy="100" r="80" fill="%238D80F0"/><ellipse cx="100" cy="90" rx="30" ry="20" fill="%23030509"/><circle cx="75" cy="85" r="8" fill="%23ffffff"/><circle cx="125" cy="85" r="8" fill="%23ffffff"/></svg>',
  talking: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><circle cx="100" cy="100" r="80" fill="%2300E5A3"/><ellipse cx="100" cy="100" rx="30" ry="25" fill="%23030509"/><circle cx="75" cy="85" r="8" fill="%23ffffff"/><circle cx="125" cy="85" r="8" fill="%23ffffff"/></svg>',
  success: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><circle cx="100" cy="100" r="80" fill="%2310b981"/><ellipse cx="100" cy="90" rx="30" ry="20" fill="%23030509"/><circle cx="75" cy="85" r="8" fill="%23ffffff"/><circle cx="125" cy="85" r="8" fill="%23ffffff"/></svg>',
  error: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><circle cx="100" cy="100" r="80" fill="%23ef4444"/><ellipse cx="100" cy="90" rx="30" ry="20" fill="%23030509"/><circle cx="75" cy="85" r="8" fill="%23ffffff"/><circle cx="125" cy="85" r="8" fill="%23ffffff"/></svg>',
};
export function StellaCompanion({
  initialPosition, theme, clickThrough = false,
  onPositionChange, onExpressionChange,
}: StellaCompanionProps) {
  const { isConnected: wsConnected, send } = useStellaConnection();
  const themeConfig = THEME_CONFIGS[theme] || THEME_CONFIGS.void;
  const [position, setPosition] = useState<CompanionPosition>(
    initialPosition ?? DEFAULT_POSITION
  );
  const [expression, setExpression] = useState<CompanionExpression>('idle');
  const [use3d, setUse3d] = useState<boolean>(true);
  const [threeRenderable, setThreeRenderable] = useState<boolean>(false);
  const [modelSrc, setModelSrc] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const setExpr = useCallback((next: CompanionExpression) => {
    if (next === expression) return;
    setExpression(next);
    onExpressionChange?.(next);
    if (wsConnected) {
      send(createWSMessage('companion.expression', {
        expression: next, ts: Date.now(),
      }));
    }
  }, [expression, wsConnected, send, onExpressionChange]);

  useEffect(() => {
    import('three').then(() => { setThreeRenderable(true); }).catch(() => setThreeRenderable(false));
    const tryLoad = async () => {
      try {
        const res = await fetch('/models/stella.glb', { method: 'HEAD' });
        if (res.ok) { setModelSrc('/models/stella.glb'); setUse3d(true); return; }
      } catch {}
      try {
        const res = await fetch('/models/stella.vrm', { method: 'HEAD' });
        if (res.ok) { setModelSrc('/models/stella.vrm'); setUse3d(true); return; }
      } catch {}
      setUse3d(false);
    };
    tryLoad();
  }, []);
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0 || clickThrough) return;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setIsDragging(true);
    setDragOffset({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  }, [clickThrough]);

  const onMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    const nx = e.clientX - dragOffset.x;
    const ny = e.clientY - dragOffset.y;
    setPosition({ x: nx, y: ny, scale: position.scale });
    onPositionChange?.({ x: nx, y: ny, scale: position.scale });
  }, [isDragging, dragOffset, position.scale, onPositionChange]);

  const onMouseUp = useCallback(() => setIsDragging(false), []);

  const onWheel = useCallback((e: React.WheelEvent) => {
    if (clickThrough) return;
    e.preventDefault();
    const newScale = Math.min(2.0, Math.max(0.5, position.scale - e.deltaY * 0.001));
    setPosition((prev) => ({ ...prev, scale: newScale }));
    onPositionChange?.({ ...position, scale: newScale });
  }, [clickThrough, position.scale, position, onPositionChange]);

  const pointerEventsStyle = clickThrough ? { pointerEvents: 'none' as const } : {};
  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed', left: position.x, top: position.y,
        width: 200 * position.scale, height: 200 * position.scale,
        zIndex: 999999, ...pointerEventsStyle, userSelect: 'none',
        touchAction: clickThrough ? 'none' : 'auto',
      }}
      onMouseDown={onMouseDown}
      onWheel={onWheel}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
      title="Stella Companion — drag to move, scroll to scale"
    >
      <div style={{
        width: '100%', height: '100%', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        borderRadius: 16 * position.scale,
        background: 'rgba(3, 5, 9, 0.6)',
        border: `1px solid ${themeConfig.primaryHex}60`,
        backdropFilter: 'blur(8px)',
        boxShadow: `0 0 40px ${themeConfig.primaryHex}40`,
        overflow: 'hidden',
      }}>
        {use3d && modelSrc && threeRenderable ? (
          <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ModelRenderer src={modelSrc} expression={expression} theme={themeConfig.primaryHex} scale={position.scale} />
          </div>
        ) : (
          <img
            src={SPRITE_BY_EXPR[expression]}
            alt={`Stella ${expression}`}
            style={{
              width: '100%', height: '100%', objectFit: 'contain',
              filter: expression === 'talking' ? 'drop-shadow(0 0 12px #00E5A3)' : 'none',
              transition: 'filter 0.2s ease',
            }}
          />
        )}
        <div style={{
          position: 'absolute', top: 4 * position.scale, right: 4 * position.scale,
          zIndex: 10, background: 'rgba(0, 0, 0, 0.75)', color: themeConfig.primaryHex,
          padding: '2px 6px', borderRadius: 10, fontSize: `${10 * position.scale}px`,
          fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.5px',
          border: `1px solid ${themeConfig.primaryHex}80`, pointerEvents: 'none',
        }}>{expression}</div>
        {!clickThrough && (
          <div style={{
            position: 'absolute', bottom: 2 * position.scale, left: '50%',
            transform: 'translateX(-50%)',
            width: DRAG_HANDLE_SIZE * position.scale, height: 4 * position.scale,
            background: 'rgba(255, 255, 255, 0.3)', borderRadius: 2 * position.scale,
            cursor: 'grab', pointerEvents: 'auto', zIndex: 5,
          }} />
        )}
      </div>
    </div>
  );
}
function ModelRenderer({
  src, expression, theme, scale = 1,
}: { src: string; expression: CompanionExpression; theme: string; scale?: number }) {
  const [threeReady, setThreeReady] = useState<'loading' | 'ready' | 'failed'>('loading');
  useEffect(() => {
    const isGlb = src.toLowerCase().endsWith('.glb');
    const isVrm = src.toLowerCase().endsWith('.vrm');
    if (!isGlb && !isVrm) { setThreeReady('failed'); return; }
    import('three').then(() => { setThreeReady('ready'); }).catch(() => setThreeReady('failed'));
  }, [src]);
  if (threeReady === 'loading') {
    return (
      <div style={{
        width: '100%', height: '100%', background: 'rgba(0,0,0,0.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ color: '#666', fontSize: `${12 * scale}px` }}>Loading model…</span>
      </div>
    );
  }
  if (threeReady === 'failed') {
    return (
      <div style={{
        width: '100%', height: '100%', background: 'rgba(0,0,0,0.3)',
        borderRadius: 16 * scale,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ color: '#666', fontSize: `${10 * scale}px` }}>3D unavailable</span>
      </div>
    );
  }
  return <div style={{ width: '100%', height: '100%' }} />;
}