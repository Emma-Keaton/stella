'use client';

import React from 'react';
import { motion } from 'motion/react';
import { AssistantTheme } from '@/lib/types';

interface StarSpinnerProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  theme?: AssistantTheme;
  text?: string;
  isSplash?: boolean;
}

export function StarSpinner({
  size = 'md',
  theme = 'rainbow',
  text,
  isSplash = false,
}: StarSpinnerProps) {
  // Theme gradients
  const themeGradients: Record<AssistantTheme, { id: string; stops: string[]; glow: string }> = {
    rainbow: {
      id: 'spinner-rainbow',
      stops: ['#00f0ff', '#00ff88', '#ffd000', '#ff007f'],
      glow: 'rgba(0, 240, 255, 0.6)',
    },
    nebula: {
      id: 'spinner-nebula',
      stops: ['#e879f9', '#a855f7', '#818cf8', '#6366f1'],
      glow: 'rgba(217, 70, 239, 0.6)',
    },
    cyan: {
      id: 'spinner-cyan',
      stops: ['#67e8f9', '#00f0ff', '#0284c7', '#3b82f6'],
      glow: 'rgba(0, 240, 255, 0.7)',
    },
    solar: {
      id: 'spinner-solar',
      stops: ['#ffe600', '#fb8500', '#ff0054', '#ff5400'],
      glow: 'rgba(255, 183, 3, 0.7)',
    },
  };

  const currentTheme = themeGradients[theme] || themeGradients.rainbow;

  const sizePixels = {
    xs: 18,
    sm: 28,
    md: 48,
    lg: 72,
    xl: 104,
  }[size];

  // Gemini 4-pointed star astroid path
  const starPath =
    'M 50 4 C 50 28.5 71.5 50 96 50 C 71.5 50 50 71.5 50 96 C 50 71.5 28.5 50 4 50 C 28.5 50 50 28.5 50 4 Z';

  const spinnerContent = (
    <div className="flex flex-col items-center justify-center gap-3">
      <div
        className="relative flex items-center justify-center"
        style={{ width: sizePixels, height: sizePixels }}
      >
        {/* Ambient Halo Glow */}
        <motion.div
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.5, 0.9, 0.5],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className="absolute inset-0 rounded-full blur-xl pointer-events-none"
          style={{ background: currentTheme.glow }}
        />

        {/* Outer Ripple Star */}
        <motion.div
          animate={{
            scale: [1, 1.5, 1.8],
            opacity: [0.6, 0.2, 0],
            rotate: [0, 45, 90],
          }}
          transition={{
            duration: 1.8,
            repeat: Infinity,
            ease: 'easeOut',
          }}
          className="absolute inset-0 pointer-events-none"
        >
          <svg viewBox="0 0 100 100" className="w-full h-full">
            <path
              d={starPath}
              fill="none"
              stroke={currentTheme.stops[0]}
              strokeWidth="2"
              strokeOpacity="0.5"
            />
          </svg>
        </motion.div>

        {/* Rotating 4-Pointer Star */}
        <motion.div
          animate={{
            rotate: 360,
            scale: [0.94, 1.06, 0.94],
          }}
          transition={{
            rotate: { duration: 2.4, repeat: Infinity, ease: 'linear' },
            scale: { duration: 1.2, repeat: Infinity, ease: 'easeInOut' },
          }}
          className="w-full h-full relative z-10"
        >
          <svg viewBox="0 0 100 100" className="w-full h-full overflow-visible drop-shadow-xl">
            <defs>
              <linearGradient
                id={`spinner-grad-${size}-${theme}`}
                x1="0%"
                y1="0%"
                x2="100%"
                y2="100%"
              >
                {currentTheme.stops.map((color, i) => (
                  <stop
                    key={i}
                    offset={`${(i / (currentTheme.stops.length - 1)) * 100}%`}
                    stopColor={color}
                  />
                ))}
              </linearGradient>
            </defs>

            <path
              d={starPath}
              fill={`url(#spinner-grad-${size}-${theme})`}
              stroke="rgba(255, 255, 255, 0.5)"
              strokeWidth="1"
            />
          </svg>
        </motion.div>
      </div>

      {text && (
        <motion.p
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-xs font-medium text-slate-300 tracking-wide flex items-center gap-2"
        >
          <span className="text-[#00f0ff] animate-pulse">●</span>
          <span>{text}</span>
        </motion.p>
      )}
    </div>
  );

  if (isSplash) {
    return (
      <div className="fixed inset-0 z-50 bg-[#030509] flex flex-col items-center justify-center p-4">
        {/* Theme-adaptive background glow flare */}
        <div
          className="absolute w-96 h-96 rounded-full blur-[140px] opacity-30 transition-all duration-700"
          style={{
            background: `radial-gradient(circle, ${currentTheme.glow} 0%, ${currentTheme.stops[1]} 50%, transparent 70%)`,
          }}
        />

        <div className="relative z-10 flex flex-col items-center justify-center space-y-6">
          <div className="flex items-center gap-2.5 mb-2">
            <span
              className="w-2.5 h-2.5 rounded-full animate-pulse"
              style={{
                backgroundColor: currentTheme.stops[0],
                boxShadow: `0 0 12px ${currentTheme.stops[0]}`,
              }}
            />
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Stella
            </h1>
            <span
              className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full border"
              style={{
                color: currentTheme.stops[0],
                borderColor: currentTheme.stops[0] + '40',
                background: currentTheme.stops[0] + '15',
              }}
            >
              v2.5 OS
            </span>
          </div>

          <StarSpinner size="xl" theme={theme} />

          <div className="space-y-1.5 text-center pt-2">
            <p className="text-sm font-semibold text-slate-100">
              {text || 'Initializing Stella...'}
            </p>
            <p className="text-xs text-slate-500 font-mono">
              Real-time voice &bull; Multi-device mesh &bull; Gemini 3.8 Flash
            </p>
          </div>
        </div>
      </div>
    );
  }

  return spinnerContent;
}
