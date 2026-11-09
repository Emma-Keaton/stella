'use client';

import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Mic,
  MicOff,
  X,
  Volume2,
  VolumeX,
  Sparkles,
  Sliders,
  Send,
  CornerDownLeft,
  ChevronDown,
  Layers,
  ArrowUpRight,
} from 'lucide-react';
import { StellaOrb } from './StellaOrb';
import { AssistantSettings, AssistantTheme, DeviceState } from '@/lib/types';
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
  const [inputText, setInputText] = useState('');
  const [showKeyboard, setShowKeyboard] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (showKeyboard && inputRef.current) {
      inputRef.current.focus();
    }
  }, [showKeyboard]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    onSubmitText(inputText.trim());
    setInputText('');
    setShowKeyboard(false);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex flex-col justify-end pointer-events-auto"
      >
        {/* Backdrop */}
        <div
          onClick={onClose}
          className="absolute inset-0 bg-black/60 backdrop-blur-md transition-opacity"
        />

        {/* Ambient background glow according to assistant theme */}
        <div
          className={`absolute inset-x-0 bottom-0 h-96 pointer-events-none transition-all ${
            settings.theme === 'rainbow'
              ? 'bg-gradient-to-t from-blue-600/20 via-emerald-500/10 to-transparent'
              : settings.theme === 'nebula'
              ? 'bg-gradient-to-t from-purple-600/20 via-fuchsia-500/10 to-transparent'
              : settings.theme === 'cyan'
              ? 'bg-gradient-to-t from-cyan-600/20 via-blue-500/10 to-transparent'
              : 'bg-gradient-to-t from-amber-600/20 via-rose-500/10 to-transparent'
          }`}
        />

        {/* Assistant Bottom Sheet Sheet */}
        <motion.div
          initial={{ y: '100%' }}
          animate={{ y: 0 }}
          exit={{ y: '100%' }}
          transition={{ type: 'spring', damping: 28, stiffness: 300 }}
          className="relative z-10 w-full max-w-xl mx-auto rounded-t-[32px] bg-[#05070d]/95 border-t-2 border-x border-[#00f0ff]/30 p-6 shadow-[0_0_40px_rgba(0,240,255,0.2)] backdrop-blur-2xl flex flex-col items-center text-center space-y-5 pb-8"
        >
          {/* Grab Handle */}
          <div className="w-12 h-1 bg-[#00f0ff]/40 rounded-full mx-auto -mt-2 mb-1 shadow-[0_0_8px_#00f0ff]" />

          {/* Top Bar inside Overlay */}
          <div className="w-full flex items-center justify-between text-xs text-slate-400 px-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold tracking-wider uppercase text-[10px] px-2.5 py-0.5 rounded-full bg-[#00f0ff]/15 text-[#00f0ff] border border-[#00f0ff]/40 shadow-[0_0_10px_rgba(0,240,255,0.2)]">
                Stella Neural Assistant
              </span>
              {screenContextTitle && (
                <span className="truncate max-w-[140px] text-[11px] text-slate-400 border-l border-slate-800 pl-2">
                  Screen: {screenContextTitle}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onOpenControls}
                className="p-1.5 rounded-full bg-[#0e1320] hover:bg-[#151c30] text-[#00f0ff] border border-[#00f0ff]/20 transition-colors shadow-sm"
                title="Device Controls"
              >
                <Sliders className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={onClose}
                className="p-1.5 rounded-full bg-[#0e1320] hover:bg-[#151c30] text-slate-300 hover:text-white border border-slate-800 transition-colors"
                title="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Central Pulsing Orb */}
          <div className="py-2">
            <StellaOrb
              isListening={isListening}
              isSpeaking={isSpeaking}
              isThinking={isThinking}
              theme={settings.theme}
              animateBackground={settings.animateBackground}
              onClick={() => {
                if (isSpeaking) {
                  stopSpeaking();
                } else if (isListening) {
                  onStopListening();
                } else {
                  onStartListening();
                }
              }}
              size="md"
            />
          </div>

          {/* Dynamic Status / Real-time Transcript / Pause feedback */}
          <div className="w-full min-h-[5.5rem] flex flex-col items-center justify-center px-4">
            {isThinking ? (
              <div className="flex items-center gap-2 text-[#00f0ff] text-sm font-medium animate-pulse drop-shadow-[0_0_8px_#00f0ff]">
                <Sparkles className="w-4 h-4 animate-spin" />
                <span>Stella is formulating response...</span>
              </div>
            ) : isListening ? (
              <div className="space-y-2">
                <div className="flex items-center justify-center gap-2">
                  {isPausing ? (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-400/50 text-emerald-300 text-[11px] font-semibold animate-pulse shadow-[0_0_12px_rgba(16,185,129,0.4)]">
                      <span className="w-2 h-2 rounded-full bg-emerald-400" />
                      Pause detected • Responding now...
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-[#00f0ff]/10 border border-[#00f0ff]/30 text-[#00f0ff] text-[10px] font-mono tracking-wider uppercase">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#00f0ff] animate-ping" />
                      Listening • Pausing will auto-send
                    </span>
                  )}
                </div>
                <p className="text-base font-medium text-white max-w-md drop-shadow">
                  {transcript || 'Say your command or ask Stella...'}
                </p>
              </div>
            ) : assistantReply ? (
              <div className="space-y-1.5">
                <p className="text-sm text-slate-100 font-medium max-w-md leading-relaxed">
                  {assistantReply}
                </p>
                {isSpeaking && (
                  <div className="flex items-center justify-center gap-1.5 text-xs text-[#ff007f] font-medium drop-shadow-[0_0_8px_rgba(255,0,127,0.4)]">
                    <Volume2 className="w-3.5 h-3.5 animate-pulse" />
                    <span>Speaking... Tap orb to stop</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-sm font-medium text-white">
                  &ldquo;Hey Stella, turn on flashlight and set volume to 80%&rdquo;
                </p>
                <p className="text-xs text-slate-400">
                  Speak naturally • Stella detects when you pause and answers automatically
                </p>
              </div>
            )}
          </div>

          {/* Bottom Action Affordances */}
          <div className="w-full pt-1">
            {showKeyboard ? (
              <form onSubmit={handleSubmit} className="flex items-center gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Type a message or device command..."
                  className="flex-1 px-4 py-2.5 rounded-full bg-[#090c16] border border-[#00f0ff]/40 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-[#00f0ff] focus:ring-1 focus:ring-[#00f0ff] shadow-inner"
                />
                <button
                  type="submit"
                  disabled={!inputText.trim()}
                  className="p-2.5 rounded-full bg-[#00f0ff] disabled:opacity-40 text-slate-950 font-bold hover:bg-[#38bdf8] transition-colors shrink-0 shadow-[0_0_15px_rgba(0,240,255,0.4)]"
                >
                  <Send className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setShowKeyboard(false)}
                  className="p-2.5 rounded-full bg-[#0e1320] text-slate-400 hover:text-white border border-slate-800 transition-colors shrink-0"
                >
                  <X className="w-4 h-4" />
                </button>
              </form>
            ) : (
              <div className="flex items-center justify-center gap-3">
                {/* Voice toggle button */}
                <button
                  type="button"
                  onClick={() => {
                    if (isListening) onStopListening();
                    else onStartListening();
                  }}
                  className={`px-5 py-2.5 rounded-full flex items-center gap-2 text-xs font-semibold transition-all ${
                    isListening
                      ? 'bg-[#ff007f] text-white shadow-[0_0_20px_rgba(255,0,127,0.5)] border border-[#ff007f]/50 animate-pulse'
                      : 'bg-gradient-to-r from-[#00f0ff] to-[#0ea5e9] text-slate-950 font-bold shadow-[0_0_20px_rgba(0,240,255,0.35)] hover:brightness-110 active:scale-95'
                  }`}
                >
                  {isListening ? (
                    <>
                      <MicOff className="w-3.5 h-3.5" />
                      <span>Stop Listening</span>
                    </>
                  ) : (
                    <>
                      <Mic className="w-3.5 h-3.5" />
                      <span>Tap to Speak</span>
                    </>
                  )}
                </button>

                {/* Keyboard input trigger */}
                <button
                  type="button"
                  onClick={() => setShowKeyboard(true)}
                  className="px-4 py-2.5 rounded-full bg-[#0a0d17] hover:bg-[#121624] border border-[#00f0ff]/30 text-[#00f0ff] hover:text-white text-xs font-medium transition-colors shadow-sm"
                >
                  Type Command
                </button>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
