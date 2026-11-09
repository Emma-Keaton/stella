'use client';

import React from 'react';

interface BatteryIndicatorProps {
  level: number;
  isCharging?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function BatteryIndicator({
  level,
  isCharging = false,
  size = 'md',
}: BatteryIndicatorProps) {
  const sizeConfig = { sm: { w: 16, h: 8 }, md: { w: 24, h: 12 }, lg: { w: 32, h: 16 } }[size];
  const color = level > 50 ? '#22c55e' : level > 20 ? '#f59e0b' : '#ef4444';

  return (
    <div className="relative flex items-center" style={{ width: sizeConfig.w, height: sizeConfig.h }}>
      <div className="absolute inset-0 rounded-sm border-2" style={{ borderColor: color }} />
      <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 rounded-sm" style={{ background: color }} />
      <div className="absolute inset-1 rounded-sm transition-all" style={{ width: `${Math.max(0, Math.min(100, level))}%`, background: color }} />
      {isCharging && <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-[6px] font-bold" style={{ color }}>âš¡</span>}
    </div>
  );
}

