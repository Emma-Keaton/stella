'use client';

import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Sparkles, Volume2, X } from 'lucide-react';
import { AssistantTheme } from '@/lib/types';
import { THEME_CONFIGS } from '@/lib/theme';

interface AskWithStellaMenuProps {
  enabled: boolean;
  onAsk: (action: string, selectedText: string) => void;
  theme?: AssistantTheme;
}

export function AskWithStellaMenu({
  enabled,
  onAsk,
  theme = 'void',
}: AskWithStellaMenuProps) {
  const themeConfig = THEME_CONFIGS[theme] || THEME_CONFIGS.void;
  const menuRef = useRef<HTMLDivElement>(null);
  const [selectedText, setSelectedText] = useState('');
  const [position, setPosition] = useState<{
    left: number;
    top: number;
    placeBelow: boolean;
  } | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const handleSelectionChange = () => {
      const selection = window.getSelection();
      const text = selection?.toString().trim();

      if (text && text.length > 2) {
        const range = selection?.getRangeAt(0);
        const rect = range?.getBoundingClientRect();

        if (rect && rect.width > 0 && rect.height > 0) {
          setSelectedText(text);

          const viewportWidth = window.innerWidth;
          const viewportHeight = window.innerHeight;

          // Measure menu dimensions if mounted, or provide mobile-safe fallback width
          const menuWidth = menuRef.current?.offsetWidth || Math.min(340, viewportWidth - 24);
          const menuHeight = menuRef.current?.offsetHeight || 52;
          const halfWidth = menuWidth / 2;

          // Directly calculate top-left origin coordinates to avoid CSS translate(-50%) layout overflow
          const rawCenterX = rect.left + rect.width / 2;
          const rawLeft = rawCenterX - halfWidth;
          const maxLeft = Math.max(12, viewportWidth - menuWidth - 12);
          const clampedLeft = Math.max(12, Math.min(rawLeft, maxLeft));

          // Vertical placement clamping
          const placeBelow = rect.top < menuHeight + 20;
          const rawTop = placeBelow ? rect.bottom + 10 : rect.top - menuHeight - 10;
          const maxTop = Math.max(12, viewportHeight - menuHeight - 12);
          const clampedTop = Math.max(12, Math.min(rawTop, maxTop));

          setPosition({
            left: clampedLeft,
            top: clampedTop,
            placeBelow,
          });
          return;
        }
      }

      setPosition(null);
    };

    const handleMouseUp = () => {
      setTimeout(handleSelectionChange, 30);
    };

    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('touchend', handleMouseUp);

    return () => {
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('touchend', handleMouseUp);
    };
  }, [enabled]);

  if (!enabled || !position || !selectedText) return null;

  return (
    <AnimatePresence>
      <motion.div
        ref={menuRef}
        initial={{ opacity: 0, scale: 0.9, y: position.placeBelow ? -6 : 6 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9, y: position.placeBelow ? -6 : 6 }}
        style={{
          position: 'fixed',
          left: `${position.left}px`,
          top: `${position.top}px`,
          zIndex: 60,
          borderColor: themeConfig.primaryHex + '55',
          boxShadow: `0 10px 35px rgba(0, 0, 0, 0.7), 0 0 20px ${themeConfig.primaryHex}30`,
        }}
        className="max-w-[calc(100vw-24px)] bg-[#0f121d]/95 border shadow-2xl backdrop-blur-2xl text-white select-none rounded-2xl sm:rounded-full p-1.5 transition-all duration-200 box-border overflow-hidden"
      >
        <div className="flex flex-wrap sm:flex-nowrap items-center gap-1.5 justify-center max-w-full overflow-hidden">
          {/* Ask Stella Badge Label */}
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold shrink-0 border"
            style={{
              background: themeConfig.primaryHex + '18',
              borderColor: themeConfig.primaryHex + '40',
              color: themeConfig.primaryHex,
            }}
          >
            <Sparkles className="w-3 h-3 animate-pulse" />
            <span className="tracking-wide whitespace-nowrap">Ask Stella</span>
          </div>

          {/* Action Buttons Bar */}
          <div className="flex items-center gap-1 max-w-full overflow-x-auto py-0.5 no-scrollbar">
            <button
              type="button"
              onClick={() => {
                onAsk('Summarize', selectedText);
                setPosition(null);
              }}
              className="px-2.5 py-1 text-[11px] font-semibold rounded-full bg-[#171b29] hover:bg-slate-700 text-slate-200 hover:text-white transition-all shrink-0 whitespace-nowrap active:scale-95 border border-slate-800 hover:border-slate-600"
            >
              Summarize
            </button>

            <button
              type="button"
              onClick={() => {
                onAsk('Polish & Fix Grammar', selectedText);
                setPosition(null);
              }}
              className="px-2.5 py-1 text-[11px] font-semibold rounded-full bg-[#171b29] hover:bg-slate-700 text-slate-200 hover:text-white transition-all shrink-0 whitespace-nowrap active:scale-95 border border-slate-800 hover:border-slate-600"
            >
              Polish
            </button>

            <button
              type="button"
              onClick={() => {
                onAsk('Explain & Research', selectedText);
                setPosition(null);
              }}
              className="px-2.5 py-1 text-[11px] font-semibold rounded-full bg-[#171b29] hover:bg-slate-700 text-slate-200 hover:text-white transition-all shrink-0 whitespace-nowrap active:scale-95 border border-slate-800 hover:border-slate-600"
            >
              Explain
            </button>

            <button
              type="button"
              onClick={() => {
                onAsk('Read Aloud with Voice', selectedText);
                setPosition(null);
              }}
              className="p-1.5 rounded-full bg-[#171b29] hover:bg-slate-700 transition-all shrink-0 active:scale-95 border border-slate-800 hover:border-slate-600"
              style={{ color: themeConfig.primaryHex }}
              title="Read Aloud with Stella Voice"
            >
              <Volume2 className="w-3.5 h-3.5" />
            </button>

            <button
              type="button"
              onClick={() => setPosition(null)}
              className="p-1.5 rounded-full text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors shrink-0"
              title="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
