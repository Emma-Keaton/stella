'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, File, Check, Download, AlertCircle } from 'lucide-react';

interface LocalGgufModel {
  fileName: string;
  fileSize: string;
  sizeBytes: number;
  architecture: string;
  quantization: string;
  contextLength: number;
  tensorCount: number;
  magicValidated: boolean;
  loadedAt: string;
  status: 'ready' | 'loading' | 'serving';
}

interface LocalGgufSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  models: LocalGgufModel[];
  selectedModel?: string;
  onSelectModel: (modelName: string) => void;
  onLoadModel: (modelName: string) => void;
  onUnloadModel: () => void;
  loadingModel?: string;
}

export function LocalGgufSelector({
  isOpen,
  onClose,
  models,
  selectedModel,
  onSelectModel,
  onLoadModel,
  onUnloadModel,
  loadingModel,
}: LocalGgufSelectorProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} transition={{ type: 'spring', damping: 25, stiffness: 300 }} className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div className="w-full max-w-2xl rounded-2xl overflow-hidden" style={{ background: 'var(--stella-surface)', border: '1px solid var(--stella-border)' }}>
              <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: 'var(--stella-border)' }}>
                <h2 className="text-xl font-semibold text-white">Local GGUF Models</h2>
                <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-800"><X className="w-5 h-5" /></button>
              </div>
              <div className="p-4">
                {models.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">No local models found</p>
                ) : (
                  <div className="space-y-3">
                    {models.map((model) => (
                      <div key={model.fileName} className="p-3 rounded-xl border" style={{ borderColor: selectedModel === model.fileName ? 'var(--stella-primary)' : 'var(--stella-border)', background: selectedModel === model.fileName ? 'var(--stella-primary)/10' : 'transparent' }}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <File className="w-5 h-5 text-slate-400" />
                            <div>
                              <p className="font-medium text-white">{model.fileName}</p>
                              <p className="text-xs text-slate-400">{model.architecture} â€¢ {model.quantization} â€¢ {model.contextLength} ctx</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {loadingModel === model.fileName && <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity }}><Download className="w-4 h-4 text-cyan-400" /></motion.div>}
                            {selectedModel === model.fileName && model.status === 'ready' && (
                              <button onClick={() => onUnloadModel()} className="px-3 py-1 rounded-lg text-xs text-slate-300 hover:text-white hover:bg-slate-800">Unload</button>
                            )}
                            {selectedModel !== model.fileName && (
                              <button onClick={() => { onSelectModel(model.fileName); onLoadModel(model.fileName); }} className="px-3 py-1 rounded-lg text-xs font-medium text-white" style={{ background: 'var(--stella-primary)' }}>Load</button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}


