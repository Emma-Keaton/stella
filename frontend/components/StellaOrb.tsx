'use client';

import React from 'react';
import { motion } from 'motion/react';
import { Mic, Sparkles } from 'lucide-react';
import { AssistantTheme } from '@/lib/types';

interface StellaOrbProps {
  isListening: boolean;
  isSpeaking: boolean;
  isThinking: boolean;
  theme: AssistantTheme;
  animateBackground: boolean;
  audioLevel?: number; // 0 to 1
  onClick?: () => void;
  size?: 'sm' | 'md' | 'lg';
}

export function StellaOrb({
  isListening,
  isSpeaking,
  isThinking,
  theme,
  animateBackground,
  audioLevel = 0,
  onClick,
  size = 'md',
}: StellaOrbProps) {
  // Theme gradients with high-vibrancy neon colors matching Stella's brand
  const themeGradients: Record<
    AssistantTheme,
    {
      gradientId: string;
      stops: Array<{ offset: string; color: string }>;
      glowRgba: string;
      secondaryGlow: string;
    }
  > = {
    rainbow: {
      gradientId: 'stella-star-rainbow',
      stops: [
        { offset: '0%', color: '#00f0ff' }, // Electric Cyan (top)
        { offset: '35%', color: '#00ff88' }, // Neon Mint
        { offset: '68%', color: '#ffd000' }, // Vibrant Solar Amber
        { offset: '100%', color: '#ff007f' }, // Hot Neon Magenta (bottom)
      ],
      glowRgba: 'rgba(0, 240, 255, 0.65)',
      secondaryGlow: 'rgba(255, 0, 127, 0.45)',
    },
    nebula: {
      gradientId: 'stella-star-nebula',
      stops: [
        { offset: '0%', color: '#e879f9' },
        { offset: '45%', color: '#a855f7' },
        { offset: '80%', color: '#6366f1' },
        { offset: '100%', color: '#ec4899' },
      ],
      glowRgba: 'rgba(217, 70, 239, 0.65)',
      secondaryGlow: 'rgba(99, 102, 241, 0.45)',
    },
    cyan: {
      gradientId: 'stella-star-cyan',
      stops: [
        { offset: '0%', color: '#67e8f9' },
        { offset: '45%', color: '#00f0ff' },
        { offset: '80%', color: '#0284c7' },
        { offset: '100%', color: '#3b82f6' },
      ],
      glowRgba: 'rgba(0, 240, 255, 0.75)',
      secondaryGlow: 'rgba(59, 130, 246, 0.45)',
    },
    solar: {
      gradientId: 'stella-star-solar',
      stops: [
        { offset: '0%', color: '#ffe600' },
        { offset: '45%', color: '#fb8500' },
        { offset: '80%', color: '#ff0054' },
        { offset: '100%', color: '#ff5400' },
      ],
      glowRgba: 'rgba(255, 183, 3, 0.7)',
      secondaryGlow: 'rgba(255, 0, 84, 0.45)',
    },
  };

  const currentTheme = themeGradients[theme] || themeGradients.rainbow;

  const sizeClasses = {
    sm: 'w-24 h-24',
    md: 'w-44 h-44',
    lg: 'w-64 h-64',
  }[size];

  // Dynamic scale based on state & audio level
  const scaleMultiplier = isSpeaking
    ? 1.06 + audioLevel * 0.16
    : isListening
    ? 1.03 + audioLevel * 0.22
    : isThinking
    ? 1.04
    : 1.0;

  // Gemini 4-pointed star astroid path coordinates
  // Top: (50, 4), Right: (96, 50), Bottom: (50, 96), Left: (4, 50)
  const starPath =
    'M 50 4 C 50 28.5 71.5 50 96 50 C 71.5 50 50 71.5 50 96 C 50 71.5 28.5 50 4 50 C 28.5 50 50 28.5 50 4 Z';

  return (
    <div
      className="relative flex items-center justify-center select-none cursor-pointer"
      onClick={onClick}
    >
      {/* Outer ambient glow halo */}
      {animateBackground && (
        <motion.div
          animate={{
            scale: isListening || isSpeaking ? [1, 1.25, 1.08] : [0.95, 1.06, 0.95],
            opacity: isListening || isSpeaking ? [0.65, 0.9, 0.65] : [0.4, 0.55, 0.4],
            rotate: isThinking ? [0, 360] : [0, 90, 180, 270, 360],
          }}
          transition={{
            duration: isThinking ? 4 : 10,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className={`absolute rounded-full blur-3xl ${sizeClasses} scale-150 pointer-events-none`}
          style={{
            background: `radial-gradient(circle, ${currentTheme.glowRgba} 0%, ${currentTheme.secondaryGlow} 50%, transparent 75%)`,
          }}
        />
      )}

      {/* Ripple ring 1 in 4-pointed star contour */}
      {(isListening || isSpeaking) && animateBackground && (
        <motion.div
          initial={{ scale: 0.85, opacity: 0.8 }}
          animate={{
            scale: [0.9, 1.45, 1.8],
            opacity: [0.75, 0.3, 0],
          }}
          transition={{
            duration: 2.2,
            repeat: Infinity,
            ease: 'easeOut',
          }}
          className={`absolute ${sizeClasses} pointer-events-none`}
        >
          <svg viewBox="0 0 100 100" className="w-full h-full">
            <path
              d={starPath}
              fill="none"
              stroke={currentTheme.stops[0].color}
              strokeWidth="1.5"
              strokeOpacity="0.45"
            />
          </svg>
        </motion.div>
      )}

      {/* Ripple ring 2 in 4-pointed star contour */}
      {(isListening || isSpeaking) && animateBackground && (
        <motion.div
          initial={{ scale: 0.85, opacity: 0.8 }}
          animate={{
            scale: [0.9, 1.4, 1.7],
            opacity: [0.7, 0.25, 0],
          }}
          transition={{
            duration: 2.2,
            delay: 1.1,
            repeat: Infinity,
            ease: 'easeOut',
          }}
          className={`absolute ${sizeClasses} pointer-events-none`}
        >
          <svg viewBox="0 0 100 100" className="w-full h-full">
            <path
              d={starPath}
              fill="none"
              stroke={currentTheme.stops[3]?.color || currentTheme.stops[1].color}
              strokeWidth="1.5"
              strokeOpacity="0.4"
            />
          </svg>
        </motion.div>
      )}

      {/* Main 4-pointed Star Button */}
      <motion.button
        type="button"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        animate={{
          scale: scaleMultiplier,
          rotate: isThinking ? [0, 180, 360] : isListening ? [-2, 2, -2] : 0,
        }}
        transition={{
          scale: { type: 'spring', stiffness: 320, damping: 20 },
          rotate: isThinking
            ? { duration: 3.5, repeat: Infinity, ease: 'linear' }
            : { duration: 1.8, repeat: Infinity, ease: 'easeInOut' },
        }}
        className={`relative ${sizeClasses} flex items-center justify-center focus:outline-none`}
        aria-label={
          isListening
            ? 'Stella is listening'
            : isSpeaking
            ? 'Stella is speaking'
            : isThinking
            ? 'Stella is thinking'
            : 'Tap Stella star to speak'
        }
      >
        <svg
          viewBox="0 0 100 100"
          className="w-full h-full overflow-visible drop-shadow-2xl"
          style={{
            filter: isListening
              ? `drop-shadow(0 0 28px ${currentTheme.glowRgba}) drop-shadow(0 0 55px ${currentTheme.secondaryGlow})`
              : isSpeaking
              ? `drop-shadow(0 0 30px ${currentTheme.glowRgba}) drop-shadow(0 0 60px ${currentTheme.secondaryGlow})`
              : isThinking
              ? 'drop-shadow(0 0 28px rgba(168, 85, 247, 0.8)) drop-shadow(0 0 50px rgba(0, 240, 255, 0.5))'
              : `drop-shadow(0 0 22px ${currentTheme.glowRgba}) drop-shadow(0 0 40px ${currentTheme.secondaryGlow})`,
          }}
        >
          <defs>
            {/* Primary Gradient across the 4 points */}
            <linearGradient
              id={currentTheme.gradientId}
              x1="10%"
              y1="5%"
              x2="90%"
              y2="95%"
            >
              {currentTheme.stops.map((stop, idx) => (
                <stop
                  key={idx}
                  offset={stop.offset}
                  stopColor={stop.color}
                />
              ))}
            </linearGradient>

            {/* Specular Core Highlight Gradient */}
            <radialGradient
              id="stella-core-light"
              cx="45%"
              cy="40%"
              r="45%"
              fx="40%"
              fy="35%"
            >
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.85" />
              <stop offset="45%" stopColor="#ffffff" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
            </radialGradient>

            {/* Inner Dark Rim for 3D bevel depth */}
            <radialGradient
              id="stella-inner-shadow"
              cx="50%"
              cy="50%"
              r="50%"
            >
              <stop offset="60%" stopColor="transparent" />
              <stop offset="100%" stopColor="#030509" stopOpacity="0.5" />
            </radialGradient>
          </defs>

          {/* Background Glow Star Layer */}
          <path
            d={starPath}
            fill={`url(#${currentTheme.gradientId})`}
            opacity="0.3"
            transform="scale(1.08) translate(-4, -4)"
            filter="blur(4px)"
          />

          {/* Solid 4-pointed Star Body */}
          <path
            d={starPath}
            fill={`url(#${currentTheme.gradientId})`}
            stroke="rgba(255, 255, 255, 0.35)"
            strokeWidth="0.8"
          />

          {/* Depth Inner Shadow */}
          <path
            d={starPath}
            fill="url(#stella-inner-shadow)"
          />

          {/* Specular Light Reflection */}
          <path
            d={starPath}
            fill="url(#stella-core-light)"
            style={{ mixBlendMode: 'overlay' }}
          />
        </svg>

        {/* Center Activity State Overlay */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10 text-slate-950">
          {isThinking ? (
            <motion.div
              animate={{ rotate: 360, scale: [0.9, 1.15, 0.9] }}
              transition={{ duration: 1.4, repeat: Infinity, ease: 'linear' }}
              className="p-2 rounded-full bg-slate-950/40 backdrop-blur-xs border border-white/40 shadow-lg text-white"
            >
              <Sparkles className="w-5 h-5 text-white drop-shadow-[0_0_8px_#ffffff]" />
            </motion.div>
          ) : isSpeaking ? (
            <div className="flex items-center gap-1 px-2.5 py-1.5 rounded-full bg-slate-950/40 backdrop-blur-xs border border-white/30 shadow-lg">
              {[0, 1, 2, 3, 4].map((i) => (
                <motion.span
                  key={i}
                  animate={{
                    height: [6, 22, 10, 26, 8][i % 5],
                  }}
                  transition={{
                    duration: 0.45,
                    repeat: Infinity,
                    repeatType: 'reverse',
                    delay: i * 0.09,
                  }}
                  className="w-1 bg-white rounded-full shadow-[0_0_6px_#ffffff]"
                  style={{ minHeight: '6px' }}
                />
              ))}
            </div>
          ) : isListening ? (
            <div className="flex flex-col items-center justify-center p-2 rounded-full bg-slate-950/45 backdrop-blur-xs border border-white/40 shadow-lg text-white">
              <Mic className="w-5 h-5 text-white animate-pulse drop-shadow-[0_0_8px_#ffffff]" />
              <div className="flex items-center gap-0.5 mt-0.5">
                {[0, 1, 2].map((i) => (
                  <motion.span
                    key={i}
                    animate={{
                      height: [3, 10, 4][i],
                    }}
                    transition={{
                      duration: 0.35,
                      repeat: Infinity,
                      repeatType: 'reverse',
                      delay: i * 0.08,
                    }}
                    className="w-0.5 bg-white rounded-full"
                    style={{ minHeight: '3px' }}
                  />
                ))}
              </div>
            </div>
          ) : (
            <div className="p-2 rounded-full bg-slate-950/35 backdrop-blur-xs border border-white/25 shadow-md text-white transition-transform hover:scale-110">
              <Mic className="w-5 h-5 text-white/95 drop-shadow-[0_0_6px_rgba(255,255,255,0.6)]" />
            </div>
          )}
        </div>
      </motion.button>
    </div>
  );
}

// Export both names for maximum compatibility
export const StellaStar = StellaOrb;
