'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, X, Volume2, VolumeX, Sparkles, Sliders, Send, CornerDownLeft, ChevronDown, Layers, ArrowUpRight } from 'lucide-react';
import { StellaOrb } from './StellaOrb';
import { AssistantSettings, DeviceState } from '@/lib/types';
import { sounds, speakText, stopSpeaking } from '@/lib/audio';

interface AssistantOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  isListening: boolean;
  isSpeaking: boolean;
  isThinking: boolean;
  transcript: string;
  assistantReply: string | null;
  settings: AssistantSettings;
  deviceState: DeviceState;
  screenContextTitle?: string | null;
  isPausing?: boolean;
  onStartListening: () => void;
  onStopListening: () => void;
  onSubmitText: (text: string) => void;
  onOpenControls: () => void;
}

export function AssistantOverlay({
  isOpen,
  onClose,
  isListening,
  isSpeaking,
  isThinking,
  transcript,
  assistantReply,
  settings,
  deviceState,
  screenContextTitle,
  isPausing = false,
  onStartListening,
  onStopListening,
  onSubmitText,
  onOpenControls,
}: AssistantOverlayProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex flex-col justify-end pointer-events-auto"
        >
          <div onClick={onClose} className="absolute inset-0 bg-black/60 backdrop-blur-md transition-opacity" />

          <div className="absolute inset-x-0 bottom-0 h-96 pointer-events-none transition-all" style={{
            background: 'linear-gradient(to top, var(--stella-primary)/20, var(--stella-secondary)/10, transparent)'
          }} />

          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 300 }}
            className="relative z-10 w-full max-w-xl mx-auto rounded-t-[32px] p-6 shadow-[0_0_40px_rgba(0,240,255,0.2)] backdrop-blur-2xl flex flex-col items-center text-center space-y-5 pb-8"
            style={{ background: 'rgba(18,20,31,0.95)', borderTop: '2px solid rgba(0,240,255,0.3)', borderLeft: '1px solid rgba(0,240,255,0.1)', borderRight: '1px solid rgba(0,240,255,0.1)' }}
          >
            <div className="relative">
              <div className="w-44 h-44 rounded-full flex items-center justify-center cursor-pointer" style={{
                background: 'radial-gradient(circle at 35% 35%, #00f0ff 0%, #00ff88 35%, #ffd000 68%, #ff007f 100%)',
                boxShadow: '0 0 40px rgba(0,240,255,0.5), 0 0 80px rgba(255,0,127,0.3), inset 0 0 20px rgba(255,255,255,0.5)',
              }}>
                <div className="absolute inset-0 rounded-full" style={{
                  background: 'radial-gradient(ellipse at 35% 35%, #00f0ff 0%, #00ff88 35%, #ffd000 68%, #ff007f 100%)',
                  opacity: 0.9,
                }} />
                <div className="relative z-10 flex items-center justify-center">
                  <div className="flex flex-col items-center">
                    <span className="text-2xl">ðŸŽ™ï¸</span>
                    <div className="flex items-center gap-1 mt-2">
                      {[0, 1, 2, 3].map((i) => (
                        <motion.span
                          key={i}
                          animate={{ height: [4, 16, 6, 20][i] }}
                          transition={{ duration: 0.35, repeat: Infinity, repeatType: 'reverse', delay: i * 0.08 }}
                          className="w-1 bg-white rounded-full"
                          style={{ minHeight: '4px' }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}


