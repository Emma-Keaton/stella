'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Sparkles,
  Mic,
  Share2,
  Cpu,
  ArrowRight,
  Check,
  Shield,
  Layers,
  Zap,
} from 'lucide-react';
import { AssistantTheme } from '@/lib/types';
import { THEME_CONFIGS } from '@/lib/theme';
import { StarSpinner } from './StarSpinner';

interface OnboardingModalProps {
  isOpen: boolean;
  onComplete: () => void;
  theme: AssistantTheme;
}

export function OnboardingModal({ isOpen, onComplete, theme }: OnboardingModalProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const themeConfig = THEME_CONFIGS[theme] || THEME_CONFIGS.rainbow;

  const steps = [
    {
      title: 'Meet Stella',
      subtitle: 'Futuristic Voice & Neural Intelligence',
      description:
        'A minimalist AI companion designed for bidirectional voice and text communication. Speak naturally—Stella streams responses token-by-token in both typing and speech synthesis.',
      badge: 'v2.5 Next-Gen OS',
      icon: <Sparkles className="w-7 h-7" />,
      features: [
        'Real-time streaming speech & dual token generation',
        'Automatic pause detection responds when you stop talking',
        'Minimalist neon dark aesthetics with zero clutter',
      ],
    },
    {
      title: 'Hands-Free Wake Word',
      subtitle: 'Say "Hey Stella" Anytime',
      description:
        'Activate hands-free voice without touching the screen. Stella listens continuously in the background and springs to life when you say "Hey Stella", "OK Stella", or "Stella".',
      badge: 'Voice Recognition',
      icon: <Mic className="w-7 h-7" />,
      features: [
        'Instant acoustic chime on wake detection',
        'Automatic 1.4s silence pause detector',
        'No popup interrupt: talks right inside the conversation stream',
      ],
    },
    {
      title: 'Device Link Hub',
      subtitle: 'Cross-Connect Up to 5 Devices',
      description:
        'Spin an 8-character connection code or scan a QR code to link your devices into a unified neural mesh. All 5 devices stay synchronized and aware of each other.',
      badge: 'Distributed Mesh',
      icon: <Share2 className="w-7 h-7" />,
      features: [
        'Generate instant 8-character link code (e.g., STL-9X4K) & QR code',
        'Delegate heavy tasks to high-power PCs and Workstations',
        'Route confidential queries to dedicated isolated vault devices',
      ],
    },
    {
      title: 'Provider & Model Freedom',
      subtitle: 'Google GenAI, NVIDIA, OpenRouter & More',
      description:
        'Bring your own API key with automated authorization testing. Stella inspects your key and unlocks only authorized, high-throughput models so you never hit cryptic errors.',
      badge: 'NVIDIA & Gemini Ready',
      icon: <Cpu className="w-7 h-7" />,
      features: [
        'Full support for NVIDIA Nemotron 70B & 340B via NIM',
        'Built-in API Key Tester with friendly human error feedback',
        'Real-time hardware toggles (Volume, DND, Timers, Flashlight)',
      ],
    },
  ];

  const handleFinish = () => {
    try {
      localStorage.setItem('stella_onboarding_completed', 'true');
    } catch {
      // ignore
    }
    onComplete();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 bg-[#030509]/90 backdrop-blur-xl flex items-center justify-center p-4 sm:p-6">
          {/* Ambient radial aura based on current theme */}
          <div
            className="absolute inset-0 pointer-events-none transition-all duration-700 opacity-60"
            style={{ background: themeConfig.bgGlowGradient }}
          />

        <motion.div
          initial={{ scale: 0.94, opacity: 0, y: 15 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.94, opacity: 0, y: 15 }}
          className="relative z-10 w-full max-w-lg bg-[#0e1117] border border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col"
        >
          {/* Header Bar */}
          <div className="px-6 pt-6 pb-4 flex items-center justify-between border-b border-slate-800/80">
            <div className="flex items-center gap-2.5">
              <StarSpinner size="xs" theme={theme} />
              <span className="text-sm font-bold tracking-tight text-white">Stella Onboarding</span>
            </div>
            <button
              type="button"
              onClick={handleFinish}
              className="text-xs text-slate-400 hover:text-slate-200 transition-colors font-medium px-2 py-1 rounded-md hover:bg-slate-800/60"
            >
              Skip
            </button>
          </div>

          {/* Slide Content */}
          <div className="p-6 sm:p-8 flex-1 flex flex-col items-center text-center space-y-6">
            {/* Step Icon / Star Showcase */}
            <div className="relative my-2">
              <div
                className="w-20 h-20 rounded-2xl flex items-center justify-center border transition-colors duration-500 shadow-xl"
                style={{
                  borderColor: themeConfig.primaryHex + '55',
                  background: `radial-gradient(circle, ${themeConfig.primaryHex}20 0%, #141721 100%)`,
                }}
              >
                <div style={{ color: themeConfig.primaryHex }}>
                  {steps[currentStep].icon}
                </div>
              </div>
            </div>

            {/* Step Title & Subtitle */}
            <div className="space-y-1.5 max-w-md">
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                {steps[currentStep].title}
              </h2>
              <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: themeConfig.primaryHex }}>
                {steps[currentStep].subtitle}
              </p>
              <p className="text-xs sm:text-sm text-slate-400 leading-relaxed pt-1">
                {steps[currentStep].description}
              </p>
            </div>

            {/* Bullet Highlights */}
            <div className="w-full bg-[#131620] border border-slate-800/80 rounded-2xl p-4 text-left space-y-2.5">
              {steps[currentStep].features.map((feat, idx) => (
                <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-300">
                  <div
                    className="w-4 h-4 rounded-full flex items-center justify-center shrink-0 mt-0.5 border"
                    style={{
                      borderColor: themeConfig.primaryHex + '70',
                      background: themeConfig.primaryHex + '20',
                      color: themeConfig.primaryHex,
                    }}
                  >
                    <Check className="w-2.5 h-2.5" />
                  </div>
                  <span className="leading-snug">{feat}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Footer Controls */}
          <div className="px-6 py-5 bg-[#0a0c10] border-t border-slate-800/80 flex items-center justify-between">
            {/* Step Indicators */}
            <div className="flex items-center gap-1.5">
              {steps.map((_, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setCurrentStep(i)}
                  className="transition-all duration-300 h-1.5 rounded-full"
                  style={{
                    width: currentStep === i ? '24px' : '8px',
                    backgroundColor: currentStep === i ? themeConfig.primaryHex : '#334155',
                  }}
                  aria-label={`Go to step ${i + 1}`}
                />
              ))}
            </div>

            {/* Next / Finish Button */}
            {currentStep < steps.length - 1 ? (
              <button
                type="button"
                onClick={() => setCurrentStep((prev) => prev + 1)}
                className={`px-5 py-2.5 rounded-xl text-white font-medium text-xs flex items-center gap-2 transition-transform active:scale-95 ${themeConfig.buttonGradient} ${themeConfig.buttonShadow}`}
              >
                <span>Continue</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleFinish}
                className={`px-6 py-2.5 rounded-xl text-white font-semibold text-xs flex items-center gap-2 transition-transform active:scale-95 ${themeConfig.buttonGradient} ${themeConfig.buttonShadow}`}
              >
                <span>Launch Stella</span>
                <Sparkles className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </motion.div>
      </div>
      )}
    </AnimatePresence>
  );
}
