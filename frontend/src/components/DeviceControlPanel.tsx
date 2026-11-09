'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Volume2, VolumeX, Sun, Monitor, Wifi, WifiOff, Bluetooth, Battery, Flashlight, Clock, Plus, AlertTriangle, Bell, Trash2 } from 'lucide-react';
import { DeviceState } from '@/lib/types';

interface DeviceControlPanelProps {
  deviceState: DeviceState;
  onUpdateState: (state: Partial<DeviceState>) => void;
  isOpen: boolean;
  onClose: () => void;
}

export function DeviceControlPanel({
  deviceState,
  onUpdateState,
  isOpen,
  onClose,
}: DeviceControlPanelProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
          <motion.aside initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', damping: 26, stiffness: 260 }} className="fixed top-0 bottom-0 right-0 z-50 w-full max-w-xs sm:max-w-sm bg-[#101216] text-white border-l border-slate-800/80 flex flex-col shadow-2xl">
            <div className="flex items-center justify-between px-5 pt-6 pb-4 border-b border-slate-800/60">
              <h2 className="text-xl font-medium tracking-tight text-white">Device Controls</h2>
              <button type="button" onClick={onClose} className="w-9 h-9 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors" aria-label="Close">
                <X className="w-5 h-5" />
              </button>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}


