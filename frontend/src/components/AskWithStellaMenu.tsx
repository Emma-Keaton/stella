'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';

interface AskWithStellaMenuProps {
  enabled: boolean;
  onAsk: () => void;
}

export function AskWithStellaMenu({
  enabled,
  onAsk,
}: AskWithStellaMenuProps) {
  if (!enabled) return null;
  return (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }} className="fixed bottom-24 right-4 z-40">
        <motion.div className="w-64 rounded-2xl p-4" style={{ background: 'var(--stella-surface)', border: '1px solid var(--stella-border)' }}>
          <p className="text-sm text-slate-300">Ask with Stella</p>
          <button onClick={onAsk} className="w-full mt-2 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: 'linear-gradient(135deg, var(--stella-primary), var(--stella-secondary))' }}>Ask Stella</button>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}


