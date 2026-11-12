'use client';

import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Volume2,
  VolumeX,
  Sun,
  Flashlight,
  Wifi,
  WifiOff,
  Bluetooth,
  Moon,
  Battery,
  BatteryCharging,
  Clock,
  CheckCircle,
  Plus,
  X,
  Play,
  Pause,
  RotateCcw,
  Sliders,
} from 'lucide-react';
import { DeviceState } from '@/lib/types';
import { sounds, stopSpeaking } from '@/lib/audio';

interface DeviceControlPanelProps {
  deviceState: DeviceState;
  onUpdateState: (newState: Partial<DeviceState>) => void;
  isOpen: boolean;
  onClose: () => void;
  /** Send a hardware control command to the device over WebSocket. */
  onDeviceCommand?: (command: string, payload: any) => void;
}

export function DeviceControlPanel({
  deviceState,
  onUpdateState,
  isOpen,
  onClose,
  onDeviceCommand,
}: DeviceControlPanelProps) {
  const [newReminderText, setNewReminderText] = useState('');
  const onUpdateStateRef = useRef(onUpdateState);

  useEffect(() => {
    onUpdateStateRef.current = onUpdateState;
  });

  // Real Battery API integration if supported by browser
  useEffect(() => {
    if (typeof window !== 'undefined' && 'getBattery' in navigator) {
      (navigator as any)
        .getBattery()
        .then((battery: any) => {
          onUpdateStateRef.current({
            batteryLevel: Math.round(battery.level * 100),
            isCharging: battery.charging,
          });

          battery.addEventListener('levelchange', () => {
            onUpdateStateRef.current({ batteryLevel: Math.round(battery.level * 100) });
          });
          battery.addEventListener('chargingchange', () => {
            onUpdateStateRef.current({ isCharging: battery.charging });
          });
        })
        .catch(() => {});
    }
  }, []);

  // Timer countdown ticker
  useEffect(() => {
    const timerInterval = setInterval(() => {
      if (deviceState.activeTimers.length === 0) return;

      let changed = false;
      const updated = deviceState.activeTimers.map((t) => {
        if (t.isRunning && t.remainingSeconds > 0) {
          changed = true;
          const next = t.remainingSeconds - 1;
          if (next === 0) {
            sounds.playConfirmChime();
          }
          return { ...t, remainingSeconds: next };
        }
        return t;
      });

      if (changed) {
        onUpdateStateRef.current({ activeTimers: updated });
      }
    }, 1000);

    return () => clearInterval(timerInterval);
  }, [deviceState.activeTimers]);

  const handleToggleFlashlight = async () => {
    const next = !deviceState.flashlight;
    onUpdateState({ flashlight: next });
    sounds.playActionChime();

    // Attempt native device camera flashlight/torch track if supported
    if (typeof window !== 'undefined' && 'mediaDevices' in navigator) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment' },
        });
        const track = stream.getVideoTracks()[0];
        if (track && 'applyConstraints' in track) {
          await (track as any).applyConstraints({
            advanced: [{ torch: next }],
          });
        }
      } catch {}
    }
  };

  const handleAddReminder = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newReminderText.trim()) return;

    const newReminder = {
      id: Date.now().toString(),
      title: newReminderText.trim(),
      completed: false,
    };
    onUpdateState({
      reminders: [...deviceState.reminders, newReminder],
    });
    setNewReminderText('');
    sounds.playActionChime();
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <>
      {/* Flashlight screen torch effect when flashlight is on */}
      {deviceState.flashlight && (
        <div className="fixed inset-0 z-40 bg-white/95 pointer-events-none mix-blend-screen animate-pulse shadow-[0_0_200px_#ffffff]" />
      )}

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 40 }}
            className="fixed inset-x-0 bottom-0 z-50 max-w-xl mx-auto p-4"
          >
            <div className="bg-[#050812]/95 backdrop-blur-2xl border-2 border-[#00f0ff]/30 rounded-3xl p-5 shadow-[0_0_40px_rgba(0,240,255,0.25)] text-slate-100 space-y-4">
              {/* Header */}
              <div className="flex items-center justify-between border-b border-[#00f0ff]/20 pb-3">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-[#00f0ff]/15 border border-[#00f0ff]/35 flex items-center justify-center text-[#00f0ff] shadow-[0_0_10px_rgba(0,240,255,0.2)]">
                    <Sliders className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white drop-shadow-[0_0_6px_rgba(255,255,255,0.2)]">
                      Device Quick Controls
                    </h3>
                    <p className="text-[11px] text-[#00f0ff]">Hardware synced with Stella</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="p-1.5 rounded-full hover:bg-[#0f172a] text-slate-400 hover:text-white transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Hardware Toggles Grid with Electric Neon */}
              <div className="grid grid-cols-4 gap-2.5">
                {/* Flashlight / Torch */}
                <button
                  type="button"
                  onClick={handleToggleFlashlight}
                  className={`p-3 rounded-2xl flex flex-col items-center justify-center gap-1.5 border transition-all ${
                    deviceState.flashlight
                      ? 'bg-amber-400/25 border-amber-400 text-amber-300 shadow-[0_0_20px_rgba(251,191,36,0.4)]'
                      : 'bg-[#090d18] border-slate-800 text-slate-400 hover:text-white hover:border-[#00f0ff]/30'
                  }`}
                >
                  <Flashlight className="w-5 h-5" />
                  <span className="text-[11px] font-medium">Torch</span>
                </button>

                {/* Wi-Fi */}
                <button
                  type="button"
                  onClick={() => {
                    onUpdateState({ wifi: !deviceState.wifi });
                    sounds.playActionChime();
                  }}
                  className={`p-3 rounded-2xl flex flex-col items-center justify-center gap-1.5 border transition-all ${
                    deviceState.wifi
                      ? 'bg-[#00f0ff]/20 border-[#00f0ff] text-[#00f0ff] shadow-[0_0_20px_rgba(0,240,255,0.35)]'
                      : 'bg-[#090d18] border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  {deviceState.wifi ? <Wifi className="w-5 h-5" /> : <WifiOff className="w-5 h-5" />}
                  <span className="text-[11px] font-medium">Wi-Fi</span>
                </button>

                {/* Bluetooth */}
                <button
                  type="button"
                  onClick={() => {
                    onUpdateState({ bluetooth: !deviceState.bluetooth });
                    sounds.playActionChime();
                  }}
                  className={`p-3 rounded-2xl flex flex-col items-center justify-center gap-1.5 border transition-all ${
                    deviceState.bluetooth
                      ? 'bg-[#818cf8]/25 border-[#818cf8] text-[#818cf8] shadow-[0_0_20px_rgba(129,140,248,0.35)]'
                      : 'bg-[#090d18] border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  <Bluetooth className="w-5 h-5" />
                  <span className="text-[11px] font-medium">Bluetooth</span>
                </button>

                {/* DND (Do Not Disturb) */}
                <button
                  type="button"
                  onClick={() => {
                    const nextDnd = !deviceState.dnd;
                    if (nextDnd) {
                      stopSpeaking();
                      onUpdateState({ dnd: true, volume: 0, isMuted: true });
                    } else {
                      onUpdateState({ dnd: false, volume: 70, isMuted: false });
                      sounds.playActionChime();
                    }
                  }}
                  className={`p-3 rounded-2xl flex flex-col items-center justify-center gap-1.5 border transition-all ${
                    deviceState.dnd
                      ? 'bg-[#d946ef]/25 border-[#d946ef] text-[#d946ef] shadow-[0_0_20px_rgba(217,70,239,0.35)]'
                      : 'bg-[#090d18] border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  <Moon className="w-5 h-5" />
                  <span className="text-[11px] font-medium">DND</span>
                </button>
              </div>

              {/* Sliders: Volume & Brightness */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-[#181b22] p-3.5 rounded-2xl border border-slate-800/80">
                {/* Volume Control */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5 text-slate-300">
                      <button
                        type="button"
                        onClick={() => {
                          const nextMute = !deviceState.isMuted;
                          onUpdateState({
                            isMuted: nextMute,
                            volume: nextMute ? 0 : 70,
                            dnd: nextMute ? deviceState.dnd : false,
                          });
                        }}
                      >
                        {deviceState.isMuted || deviceState.volume === 0 || deviceState.dnd ? (
                          <VolumeX className="w-4 h-4 text-rose-400" />
                        ) : (
                          <Volume2 className="w-4 h-4 text-cyan-400" />
                        )}
                      </button>
                      <span>Volume</span>
                    </div>
                    <span className="text-slate-400 font-mono">
                      {deviceState.dnd
                        ? 'DND Active (Muted)'
                        : deviceState.isMuted
                        ? 'Muted'
                        : `${deviceState.volume}%`}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={deviceState.isMuted || deviceState.dnd ? 0 : deviceState.volume}
                    onChange={(e) => {
                      const val = parseInt(e.target.value);
                      onUpdateState({
                        volume: val,
                        isMuted: val === 0,
                        dnd: val > 0 ? false : deviceState.dnd,
                      });
                      onDeviceCommand?.('volume', { level: val });
                    }}
                    className="w-full h-1.5 bg-slate-700 rounded-lg accent-cyan-400 cursor-pointer"
                  />
                </div>

                {/* Brightness Control */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5 text-slate-300">
                      <Sun className="w-4 h-4 text-amber-400" />
                      <span>Brightness</span>
                    </div>
                    <span className="text-slate-400 font-mono">
                      {deviceState.brightness}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="100"
                    value={deviceState.brightness}
                    onChange={(e) => {
                      const val = parseInt(e.target.value);
                      onUpdateState({ brightness: val });
                      onDeviceCommand?.('brightness', { level: val });
                    }}
                    className="w-full h-1.5 bg-slate-700 rounded-lg accent-amber-400 cursor-pointer"
                  />
                </div>
              </div>

              {/* Battery status bar */}
              <div className="flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-[#181b22] border border-slate-800 text-xs">
                <div className="flex items-center gap-2 text-slate-300">
                  {deviceState.isCharging ? (
                    <BatteryCharging className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <Battery className="w-4 h-4 text-cyan-400" />
                  )}
                  <span>Device Battery</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-white">
                    {deviceState.batteryLevel}%
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {deviceState.isCharging ? 'Charging' : 'On battery'}
                  </span>
                </div>
              </div>

              {/* Active Timers */}
              {deviceState.activeTimers.length > 0 && (
                <div className="space-y-2">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Active Timers
                  </span>
                  <div className="space-y-1.5">
                    {deviceState.activeTimers.map((timer) => (
                      <div
                        key={timer.id}
                        className="flex items-center justify-between p-2.5 rounded-xl bg-[#181b22] border border-slate-800 text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4 text-cyan-400 animate-pulse" />
                          <span className="text-white font-medium">{timer.label}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-base font-bold text-cyan-300">
                            {formatTime(timer.remainingSeconds)}
                          </span>
                          <button
                            type="button"
                            onClick={() => {
                              onUpdateState({
                                activeTimers: deviceState.activeTimers.filter(
                                  (t) => t.id !== timer.id
                                ),
                              });
                            }}
                            className="p-1 rounded-md hover:bg-slate-800 text-slate-400 hover:text-rose-400"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Reminders snippet */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Reminders
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {deviceState.reminders.filter((r) => !r.completed).length} pending
                  </span>
                </div>

                <div className="max-h-28 overflow-y-auto space-y-1">
                  {deviceState.reminders.map((rem) => (
                    <div
                      key={rem.id}
                      onClick={() => {
                        const updated = deviceState.reminders.map((r) =>
                          r.id === rem.id ? { ...r, completed: !r.completed } : r
                        );
                        onUpdateState({ reminders: updated });
                      }}
                      className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs cursor-pointer transition-colors ${
                        rem.completed
                          ? 'bg-[#15171d] text-slate-400 line-through'
                          : 'bg-[#181b22] text-slate-200 hover:bg-[#1e222b]'
                      }`}
                    >
                      <CheckCircle
                        className={`w-3.5 h-3.5 shrink-0 ${
                          rem.completed ? 'text-slate-400' : 'text-cyan-400'
                        }`}
                      />
                      <span className="truncate">{rem.title}</span>
                    </div>
                  ))}
                </div>

                <form onSubmit={handleAddReminder} className="flex gap-2 pt-1">
                  <input
                    type="text"
                    value={newReminderText}
                    onChange={(e) => setNewReminderText(e.target.value)}
                    placeholder="Add reminder..."
                    className="flex-1 bg-[#181b22] border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
                  />
                  <button
                    type="submit"
                    className="px-3 py-1.5 rounded-xl bg-cyan-500 text-slate-950 font-medium text-xs hover:bg-cyan-400 transition-colors shrink-0"
                  >
                    Add
                  </button>
                </form>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
