'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const STELLA_BRAND_COLORS = [
  '#00F0FF',
  '#00E5A3',
  '#8D80F0',
  '#FF007F',
];

interface StarSpinnerProps {
  size?: number;
  thickness?: number;
  speed?: number;
  className?: string;
}

export function StarSpinner({
  size = 48,
  thickness = 3,
  speed = 1.2,
  className = '',
}: StarSpinnerProps) {
  const [colorIndex, setColorIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setColorIndex((prev) => (prev + 1) % STELLA_BRAND_COLORS.length);
    }, 800);
    return () => clearInterval(interval);
  }, []);

  const currentColor = STELLA_BRAND_COLORS[colorIndex];
  const nextColor = STELLA_BRAND_COLORS[(colorIndex + 1) % STELLA_BRAND_COLORS.length];

  return (
    <motion.svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 100 100"
      animate={{ rotate: 360 }}
      transition={{ duration: speed, repeat: Infinity, ease: 'linear' }}
      style={{ filter: `drop-shadow(0 0 ${size * 0.1}px ${currentColor}80) drop-shadow(0 0 ${size * 0.2}px ${currentColor}40)` }}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="starGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={currentColor} stopOpacity={1} />
          <stop offset="100%" stopColor={nextColor} stopOpacity={1} />
        </linearGradient>
      </defs>
      <path
        d="M50 5 L60 40 L95 40 L68 62 L78 95 L50 75 L22 95 L32 62 L5 40 L40 40 Z"
        fill="none"
        stroke="url(#starGradient)"
        strokeWidth={thickness}
        strokeLinecap="round"
        strokeLinejoin="round"
        filter="drop-shadow(0 0 4px currentColor)"
      />
      <path
        d="M50 15 L56 40 L85 40 L63 57 L70 82 L50 65 L30 82 L37 57 L15 40 L44 40 Z"
        fill="none"
        stroke={currentColor}
        strokeWidth={thickness * 0.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0.6}
        style={{ filter: `blur(${thickness * 0.5}px)` }}
      />
      <motion.circle
        cx="50"
        cy="50"
        r={size * 0.06}
        fill={currentColor}
        animate={{
          scale: [1, 1.5, 1],
          opacity: [0.8, 0.3, 0.8],
        }}
        transition={{
          duration: speed * 0.5,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
    </motion.svg>
  );
}

export function StarSpinnerMini({
  size = 24,
  thickness = 2,
  speed = 1,
  className = '',
}: StarSpinnerProps) {
  const [colorIndex, setColorIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setColorIndex((prev) => (prev + 1) % STELLA_BRAND_COLORS.length);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const currentColor = STELLA_BRAND_COLORS[colorIndex];

  return (
    <motion.svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 100 100"
      animate={{ rotate: 360 }}
      transition={{ duration: speed, repeat: Infinity, ease: 'linear' }}
      style={{ filter: `drop-shadow(0 0 ${size * 0.15}px ${currentColor}60)` }}
      aria-hidden="true"
    >
      <path
        d="M50 8 L58 38 L92 38 L65 58 L73 88 L50 70 L27 88 L35 58 L8 38 L42 38 Z"
        fill="none"
        stroke={currentColor}
        strokeWidth={thickness}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </motion.svg>
  );
}


