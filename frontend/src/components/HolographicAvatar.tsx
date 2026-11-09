'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { AssistantTheme } from '@/lib/types';

interface HolographicAvatarProps {
  isListening: boolean;
  isSpeaking: boolean;
  isThinking: boolean;
  theme: AssistantTheme;
  animateBackground: boolean;
  audioLevel?: number;
  onClick?: () => void;
  size?: 'sm' | 'md' | 'lg';
}

export function HolographicAvatar({
  isListening,
  isSpeaking,
  isThinking,
  theme,
  animateBackground,
  audioLevel = 0,
  onClick,
  size = 'md',
}: HolographicAvatarProps) {
  const themeColors: Record<AssistantTheme, { primary: string; secondary: string; accent: string; glow: string }> = {
    void: { primary: '#00E5A3', secondary: '#00F0FF', accent: '#8D80F0', glow: 'rgba(0,229,163,0.6)' },
    oled: { primary: '#00E5A3', secondary: '#00F0FF', accent: '#8D80F0', glow: 'rgba(0,229,163,0.5)' },
    aurora: { primary: '#6C5EE0', secondary: '#8D80F0', accent: '#00E5A3', glow: 'rgba(108,94,224,0.6)' },
    solar: { primary: '#FBBF24', secondary: '#FB8500', accent: '#EF4444', glow: 'rgba(251,191,36,0.6)' },
    light: { primary: '#007A57', secondary: '#007C8A', accent: '#5A4BD1', glow: 'rgba(0,122,87,0.4)' },
  };

  const colors = themeColors[theme] || themeColors.void;
  const sizeConfig = { sm: { w: 80, h: 80 }, md: { w: 140, h: 140 }, lg: { w: 200, h: 200 } }[size];
  const baseScale = isSpeaking ? 1.08 + audioLevel * 0.2 : isListening ? 1.05 + audioLevel * 0.25 : isThinking ? 1.04 : 1.0;

  return (
    <motion.div
      animate={{ rotate: isThinking ? 360 : 0 }}
      transition={{ rotate: { duration: 8, repeat: Infinity, ease: 'linear' } }}
      className="relative flex items-center justify-center cursor-pointer"
      style={{ width: sizeConfig.w, height: sizeConfig.h, borderRadius: '50%', boxShadow: isListening ? `0 0 60px ${colors.glow}` : `0 0 40px ${colors.glow}` }}
      onClick={onClick}
      whileTap={{ scale: 0.95 }}
    >
      <div
        className="absolute inset-0 rounded-full"
        style={{ background: `radial-gradient(ellipse at 30% 30%, ${colors.primary} 0%, ${colors.secondary} 40%, ${colors.accent} 80%, transparent 100%)`, opacity: 0.9 }}
      />
      <div className="relative z-10 flex flex-col items-center justify-center">
        {isThinking && <div className="text-white">Thinking...</div>}
        {isSpeaking && <div className="text-white">Speaking...</div>}
        {isListening && <div className="text-white">Listening...</div>}
        {!isThinking && !isSpeaking && !isListening && <div className="text-white">Ready</div>}
      </div>
    </motion.div>
  );
}


