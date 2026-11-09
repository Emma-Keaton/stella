'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';

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
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} transition={{ type: 'spring', damping: 25, stiffness: 300 }} className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div className="w-full max-w-lg rounded-2xl overflow-hidden" style={{ background: 'var(--stella-surface)', border: '1px solid var(--stella-border)' }}>
              <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: 'var(--stella-border)' }}>
                <h2 className="text-xl font-semibold text-white">Screen Context</h2>
                <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-800"><X className="w-5 h-5" /></button>
              </div>
              <div className="p-4">Screen context simulator</div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}


