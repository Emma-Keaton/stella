'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ArrowRight } from 'lucide-react';

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
}

export function OnboardingModal({
  isOpen,
  onClose,
  onComplete,
}: OnboardingModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} transition={{ type: 'spring', damping: 25, stiffness: 300 }} className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div className="w-full max-w-lg rounded-2xl overflow-hidden" style={{ background: 'var(--stella-surface)', border: '1px solid var(--stella-border)' }}>
              <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: 'var(--stella-border)' }}>
                <h2 className="text-xl font-semibold text-white">Welcome to Stella</h2>
                <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-800"><X className="w-5 h-5" /></button>
              </div>
              <div className="p-8 text-center">
                <p className="text-slate-300 mb-6">Onboarding modal content</p>
                <button onClick={() => { onComplete(); onClose(); }} className="px-6 py-3 rounded-xl font-semibold text-white" style={{ background: 'linear-gradient(135deg, var(--stella-primary), var(--stella-secondary))' }}>Get Started <ArrowRight className="w-4 h-4 inline ml-2" /></button>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}


