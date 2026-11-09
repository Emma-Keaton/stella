'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  ArrowLeft,
  CheckCircle2,
  Mic,
  Camera,
  Layers,
  HelpCircle,
  Sliders,
  ShieldCheck,
  ChevronRight,
  Sun,
  Palette,
} from 'lucide-react';
import { AssistantSettings } from '@/lib/types';
import { THEME_CONFIGS } from '@/lib/theme';

interface DeviceAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AssistantSettings;
  onUpdateSettings: (newSettings: Partial<AssistantSettings>) => void;
  onTriggerAssistant: () => void;
}

export function DeviceAssistantModal({
  isOpen,
  onClose,
  settings,
  onUpdateSettings,
  onTriggerAssistant,
}: DeviceAssistantModalProps) {
  const themeConfig = THEME_CONFIGS[settings.theme] || THEME_CONFIGS.void;
  const [showOsPrompt, setShowOsPrompt] = useState(false);
  const [showSetupHelp, setShowSetupHelp] = useState(false);


  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 15 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-50 bg-[#0d0f14] text-slate-100 overflow-y-auto"
        >
          {/* Top Bar matching screenshot 5 */}
          <div className="sticky top-0 z-20 bg-[#0d0f14]/90 backdrop-blur-md px-4 py-4 border-b border-slate-800/80 flex items-center justify-between max-w-2xl mx-auto">
            <button
              type="button"
              onClick={onClose}
              className="p-2 -ml-2 rounded-full hover:bg-slate-800/80 text-slate-300 hover:text-white transition-colors"
              aria-label="Go back"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-base font-semibold text-white tracking-tight">
              Device Assistant
            </h1>
            <div className="w-9" /> {/* Spacer */}
          </div>

          <div className="max-w-2xl mx-auto px-4 py-6 space-y-7 pb-20">
            {/* Section: DEFAULT ASSISTANT */}
            <div className="space-y-2">
              <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase px-1">
                Default Assistant
              </span>

              <div className="p-4 rounded-2xl bg-[#15181f] border border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 border"
                    style={{
                      color: themeConfig.primaryHex,
                      borderColor: themeConfig.primaryHex + '50',
                      background: themeConfig.primaryHex + '15',
                    }}
                  >
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold text-white">
                      {settings.isDefaultAssistant
                        ? 'Stella is your default assistant'
                        : 'Set Stella as default assistant'}
                    </h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {settings.isDefaultAssistant
                        ? 'Handles wake words, home button hold, and screen gestures'
                        : 'Enable full device control and wake gestures'}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setShowOsPrompt(true)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-white transition-colors shrink-0 border"
                  style={{
                    borderColor: themeConfig.primaryHex + '60',
                    background: themeConfig.primaryHex + '20',
                  }}
                >
                  {settings.isDefaultAssistant ? 'Change' : 'Set Default'}
                </button>
              </div>

              <button
                type="button"
                onClick={() => setShowSetupHelp(!showSetupHelp)}
                className="inline-flex items-center gap-1.5 text-xs text-slate-400 transition-colors px-1 py-1 hover:text-white"
                style={{ color: showSetupHelp ? themeConfig.primaryHex : undefined }}
              >
                <span>Need help setting up?</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>

              {showSetupHelp && (
                <div className="p-4 rounded-xl bg-[#12141a] border border-slate-800/80 text-xs text-slate-300 space-y-2.5">
                  <p className="font-medium text-white">
                    Setting Stella as Default Digital Assistant:
                  </p>
                  <ol className="list-decimal pl-4 space-y-1 text-slate-400">
                    <li>Open your device’s System Settings &gt; Apps &gt; Default Apps</li>
                    <li>Tap &ldquo;Digital assistant app&rdquo; or &ldquo;Device assistant app&rdquo;</li>
                    <li>Select &ldquo;Stella&rdquo; from the assistant list</li>
                    <li>
                      Grant permissions for Voice input, Screen capture context, and Device
                      controls
                    </li>
                  </ol>
                  <p className="text-[11px] font-mono pt-1" style={{ color: themeConfig.primaryHex }}>
                    Once selected, long-pressing your power/home button or saying &ldquo;Hey
                    Stella&rdquo; invokes Stella immediately!
                  </p>
                </div>
              )}
            </div>

            {/* Section: WHEN THE ASSISTANT OPENS */}
            <div className="space-y-3">
              <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase px-1">
                When the Assistant Opens
              </span>

              <div className="rounded-2xl bg-[#15181f] border border-slate-800 divide-y divide-slate-800/80 overflow-hidden">
                {/* Start listening toggle */}
                <div className="p-4 flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <Mic className="w-5 h-5 mt-0.5 shrink-0" style={{ color: themeConfig.primaryHex }} />
                    <div>
                      <h3 className="text-sm font-medium text-white">Start listening</h3>
                      <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                        Start the microphone as soon as you invoke the assistant.
                      </p>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer shrink-0 mt-0.5">
                    <input
                      type="checkbox"
                      checked={settings.startListeningOnOpen}
                      onChange={(e) =>
                        onUpdateSettings({ startListeningOnOpen: e.target.checked })
                      }
                      className="sr-only peer"
                    />
                    <div
                      className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all"
                      style={{
                        backgroundColor: settings.startListeningOnOpen
                          ? themeConfig.primaryHex
                          : undefined,
                      }}
                    />
                  </label>
                </div>

                {/* Attach screenshot toggle */}
                <div className="p-4 flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <Camera className="w-5 h-5 mt-0.5 shrink-0" style={{ color: themeConfig.primaryHex }} />
                    <div>
                      <h3 className="text-sm font-medium text-white">Attach screenshot</h3>
                      <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                        Attach a screenshot of the screen on invocation. Needs a model that can see
                        images, and &ldquo;Use screenshot&rdquo; turned on in the digital assistant settings.
                      </p>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer shrink-0 mt-0.5">
                    <input
                      type="checkbox"
                      checked={settings.attachScreenshotOnInvoke}
                      onChange={(e) =>
                        onUpdateSettings({ attachScreenshotOnInvoke: e.target.checked })
                      }
                      className="sr-only peer"
                    />
                    <div
                      className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all"
                      style={{
                        backgroundColor: settings.attachScreenshotOnInvoke
                          ? themeConfig.primaryHex
                          : undefined,
                      }}
                    />
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* OS Default Assistant Simulation Dialog */}
          {showOsPrompt && (
            <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
              <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="w-full max-w-sm rounded-2xl bg-[#181a22] border border-slate-700/80 p-5 space-y-4 shadow-2xl"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                    <ShieldCheck className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white text-sm">
                      Set Stella as Default Assistant?
                    </h3>
                    <p className="text-xs text-slate-400">Android / Device Assistant Settings</p>
                  </div>
                </div>

                <div className="text-xs text-slate-300 leading-relaxed bg-[#12141a] p-3 rounded-xl border border-slate-800 space-y-1.5">
                  <p>Stella will replace the current default assistant and receive:</p>
                  <ul className="list-disc pl-4 space-y-1 text-slate-400">
                    <li>System microphone and wake word detection</li>
                    <li>Screen capture context when invoked</li>
                    <li>Hardware control permissions (Volume, Torch, Wi-Fi)</li>
                  </ul>
                </div>

                <div className="flex items-center justify-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => setShowOsPrompt(false)}
                    className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onUpdateSettings({ isDefaultAssistant: true });
                      setShowOsPrompt(false);
                    }}
                    className="px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-xs font-semibold text-slate-950 transition-colors"
                  >
                    Set as Default
                  </button>
                </div>
              </motion.div>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
