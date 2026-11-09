'use client';

import React from 'react';
import { Battery, BatteryCharging, Zap, BatteryLow, BatteryMedium, BatteryFull } from 'lucide-react';
import { DeviceState, AssistantTheme } from '@/lib/types';
import { THEME_CONFIGS } from '@/lib/theme';

interface BatteryIndicatorProps {
  deviceState: DeviceState;
  theme?: AssistantTheme;
  onClick?: () => void;
}

export function BatteryIndicator({
  deviceState,
  theme = 'rainbow',
  onClick,
}: BatteryIndicatorProps) {
  const themeConfig = THEME_CONFIGS[theme] || THEME_CONFIGS.rainbow;
  const level = Math.min(100, Math.max(0, deviceState.batteryLevel ?? 92));
  const isCharging = deviceState.isCharging;
  const isLow = level <= 20;

  // Determine fill color & status
  let statusColor = themeConfig.primaryHex;
  if (isLow) statusColor = '#f43f5e'; // Rose red for low battery
  else if (deviceState.lowPowerMode || level <= 35) statusColor = '#fbbf24'; // Amber for warning/power save
  else if (isCharging) statusColor = '#10b981'; // Emerald for charging

  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-mono font-medium transition-all hover:scale-105 active:scale-95 group shrink-0"
      style={{
        background: `${statusColor}15`,
        borderColor: `${statusColor}40`,
        color: statusColor,
        boxShadow: `0 0 12px ${statusColor}18`,
      }}
      title={`Battery: ${level}% ${isCharging ? '(Charging)' : ''} ${deviceState.lowPowerMode ? '• Low Power Mode' : ''} - Click for Hardware Controls`}
    >
      {/* Icon with pulse effect if charging */}
      <div className="relative flex items-center justify-center">
        {isCharging ? (
          <Zap className="w-3.5 h-3.5 animate-pulse text-amber-400" />
        ) : level > 75 ? (
          <BatteryFull className="w-4 h-4" />
        ) : level > 30 ? (
          <BatteryMedium className="w-4 h-4" />
        ) : (
          <BatteryLow className="w-4 h-4 text-rose-400 animate-pulse" />
        )}
      </div>

      {/* Visual Level Bar inside small battery shell */}
      <div className="w-5 h-2.5 rounded-sm border border-current p-[1px] relative flex items-center">
        <div
          className="h-full rounded-[1px] transition-all duration-500"
          style={{
            width: `${level}%`,
            backgroundColor: statusColor,
          }}
        />
        {/* Terminal nub */}
        <div
          className="absolute -right-[3px] top-[2px] w-[2px] h-[3px] rounded-r-[1px]"
          style={{ backgroundColor: statusColor }}
        />
      </div>

      {/* Percentage Pill */}
      <span className="font-bold text-[11px] tracking-tight">
        {level}%
      </span>
    </button>
  );
}
