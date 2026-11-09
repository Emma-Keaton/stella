'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Monitor,
  Camera,
  X,
  Sparkles,
  Plane,
  Mail,
  MapPin,
  FileCode,
  ArrowRight,
  Upload,
} from 'lucide-react';

interface ScreenContextSimulatorProps {
  isOpen: boolean;
  onClose: () => void;
  onAttachContext: (contextText: string, title: string) => void;
}

export function ScreenContextSimulator({
  isOpen,
  onClose,
  onAttachContext,
}: ScreenContextSimulatorProps) {
  const [selectedScenario, setSelectedScenario] = useState<string>('flight');
  const [customText, setCustomText] = useState('');

  const sampleScreens = [
    {
      id: 'flight',
      title: 'Flight Itinerary (Skyline Airways)',
      icon: Plane,
      description: 'Flight SA-408 from Lagos to London Heathrow. Departs 08:30 Nov 12, Terminal 2. Seat 14A. Gate B12.',
      context: 'Active Screen: Airline App displaying Boarding Pass. Flight SA-408, Lagos (LOS) to London Heathrow (LHR). Departure: Nov 12, 08:30 AM. Gate B12, Boarding at 07:45 AM. Seat: 14A (Window). Baggage: 2 checked bags included.',
    },
    {
      id: 'email',
      title: 'Sales Email from John Doe',
      icon: Mail,
      description: 'Email from j.doe@apexcorp.com asking for local AI assistant rollout timelines and pricing tiers.',
      context: 'Active Screen: Gmail app displaying incoming email from John Doe (VP Ops, Apex Corp): "Hi team, we are evaluating local AI assistant models and on-device privacy for our 450 mobile reps. Could you send the architecture doc, pricing tiers, and estimated rollout schedule by Friday?"',
    },
    {
      id: 'travel',
      title: 'Travel Guide: Benin City, Edo State',
      icon: MapPin,
      description: 'Tourism page showing Oba Palace, National Museum, and Igun Bronze Street artisans.',
      context: 'Active Screen: Travel blog "Discovering Benin City, Edo State". Highlights: Royal Oba Palace, National Museum with ancient bronze castings, historic Igun Street bronze smiths guild, Kada Cinema & Plaza, and Okomu National Park eco-safari.',
    },
    {
      id: 'code',
      title: 'Next.js App Router Component',
      icon: FileCode,
      description: 'Code editor showing React 19 Client Component with voice recognition hook.',
      context: 'Active Screen: VS Code showing TypeScript component with SpeechRecognition API and custom audio waveform hooks.',
    },
  ];

  const handleApply = () => {
    if (selectedScenario === 'custom' && customText.trim()) {
      onAttachContext(customText.trim(), 'Custom Screen Snippet');
    } else {
      const found = sampleScreens.find((s) => s.id === selectedScenario);
      if (found) {
        onAttachContext(found.context, found.title);
      }
    }
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="w-full max-w-lg bg-[#14161f] border border-slate-700/80 rounded-3xl p-5 space-y-4 shadow-2xl text-slate-100"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                  <Monitor className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">
                    Screen Context Assistant
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    &ldquo;Use screenshot&rdquo; digital assistant simulation
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="p-1.5 rounded-full hover:bg-slate-800 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-300">
              When Stella is invoked as the default device assistant, she can analyze the active screen in the background to provide instant contextual answers.
            </p>

            {/* Presets */}
            <div className="space-y-2">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Select Active Screen Simulation:
              </span>
              <div className="grid grid-cols-1 gap-2 max-h-56 overflow-y-auto">
                {sampleScreens.map((s) => {
                  const Icon = s.icon;
                  const isSelected = selectedScenario === s.id;
                  return (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => setSelectedScenario(s.id)}
                      className={`w-full p-3 rounded-xl border text-left transition-all flex items-start gap-3 ${
                        isSelected
                          ? 'bg-cyan-500/10 border-cyan-500/40 shadow-sm'
                          : 'bg-[#181b24] border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div
                        className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                          isSelected
                            ? 'bg-cyan-400 text-slate-950 font-bold'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className="flex-1 truncate">
                        <div className="text-xs font-semibold text-white truncate">
                          {s.title}
                        </div>
                        <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">
                          {s.description}
                        </p>
                      </div>
                    </button>
                  );
                })}

                {/* Custom screen text option */}
                <button
                  type="button"
                  onClick={() => setSelectedScenario('custom')}
                  className={`w-full p-3 rounded-xl border text-left transition-all flex items-start gap-3 ${
                    selectedScenario === 'custom'
                      ? 'bg-cyan-500/10 border-cyan-500/40'
                      : 'bg-[#181b24] border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                      selectedScenario === 'custom'
                        ? 'bg-cyan-400 text-slate-950 font-bold'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    <Upload className="w-4 h-4" />
                  </div>
                  <div className="flex-1">
                    <div className="text-xs font-semibold text-white">
                      Custom Screen Text or Document
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Paste text from any article, receipt, or chat window
                    </p>
                  </div>
                </button>
              </div>

              {selectedScenario === 'custom' && (
                <textarea
                  value={customText}
                  onChange={(e) => setCustomText(e.target.value)}
                  placeholder="Paste screen content, email text, or receipt details here..."
                  rows={3}
                  className="w-full bg-[#181b24] border border-slate-800 rounded-xl p-3 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
                />
              )}
            </div>

            {/* CTA */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApply}
                className="px-4 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs transition-colors flex items-center gap-1.5 shadow-lg shadow-cyan-500/20"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Attach to Stella Context</span>
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
