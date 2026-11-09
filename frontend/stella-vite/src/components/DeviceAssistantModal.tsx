'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Sparkles, Settings as SettingsIcon, Mic, Sliders, Shield, Zap } from 'lucide-react';
import { AssistantSettings, AssistantTheme } from '@/lib/types';

interface DeviceAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AssistantSettings;
  onUpdateSettings: (settings: Partial<AssistantSettings>) => void;
  onTriggerAssistant: () => void;
}

export function DeviceAssistantModal({
  isOpen,
  onClose,
  settings,
  onUpdateSettings,
  onTriggerAssistant,
}: DeviceAssistantModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} transition={{ type: 'spring', damping: 25, stiffness: 300 }} className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div className="w-full max-w-lg rounded-2xl overflow-hidden" style={{ background: 'var(--stella-surface)', border: '1px solid var(--stella-border)' }}>
              <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: 'var(--stella-border)' }}>
                <h2 className="text-xl font-semibold text-white">Device Assistant</h2>
                <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-800"><X className="w-5 h-5" /></button>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(0,229,163,0.1)' }}>
                      <Sparkles className="w-5 h-5 text-cyan-300" />
                    </div>
                    <div>
                      <p className="font-medium text-white">Device Assistant</p>
                      <p className="text-xs text-slate-400">Control your device with voice</p>
                    </div>
                  </div>
                </div>
                <button onClick={onTriggerAssistant} className="w-full py-3 rounded-xl font-semibold text-white" style={{ background: 'linear-gradient(135deg, var(--stella-primary), var(--stella-secondary))' }}>
                  <Mic className="w-5 h-5 inline mr-2" /> Activate Voice
                </button>
                <div className="p-4 rounded-xl" style={{ background: 'var(--stella-surface-raised)', border: '1px solid var(--stella-border)' }}>
                  <h3 className="font-medium text-white mb-3">Capabilities</h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="flex items-center gap-2 text-slate-300"><Sliders className="w-4 h-4" /><span>Device Controls</span></div>
                    <div className="flex items-center gap-2 text-slate-300"><Shield className="w-4 h-4" /><span>Privacy Mode</span></div>
                    <div className="flex items-center gap-2 text-slate-300"><Zap className="w-4 h-4" /><span>Quick Actions</span></div>
                    <div className="flex items-center gap-2 text-slate-300"><SettingsIcon className="w-4 h-4" /><span>Settings</span></div>
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}


