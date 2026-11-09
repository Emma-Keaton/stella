'use client';

import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X, Clock, Settings as SettingsIcon, Plus, QrCode, ChevronDown, ChevronRight, MessageSquare, Sparkles, Smartphone, Trash2 } from 'lucide-react';
import { Workspace } from '@/lib/types';

interface WorkspacesDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  workspaces: Workspace[];
  activeWorkspaceId: string;
  activeThreadId: string;
  onSelectWorkspace: (id: string) => void;
  onSelectThread: (threadId: string) => void;
  onNewThread: (isDeviceAssistant?: boolean) => void;
  onNewWorkspace: () => void;
  onOpenSettings: () => void;
  onDeleteThread?: (threadId: string) => void;
}

export function WorkspacesDrawer({
  isOpen,
  onClose,
  workspaces,
  activeWorkspaceId,
  activeThreadId,
  onSelectWorkspace,
  onSelectThread,
  onNewThread,
  onNewWorkspace,
  onOpenSettings,
  onDeleteThread,
}: WorkspacesDrawerProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
        />

        <motion.div
          initial={{ x: '-100%' }}
          animate={{ x: 0 }}
          exit={{ x: '-100%' }}
          transition={{ type: 'spring', damping: 26, stiffness: 260 }}
          className="fixed top-0 bottom-0 left-0 z-50 w-full max-w-xs sm:max-w-sm bg-[#101216] text-white border-r border-slate-800/80 flex flex-col shadow-2xl"
        >
          <div className="flex items-center justify-between px-5 pt-6 pb-4 border-b border-slate-800/60">
            <h2 className="text-xl font-medium tracking-tight text-white">Workspaces</h2>
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => {}} title="Chat history" className="w-9 h-9 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors">
                <Clock className="w-5 h-5" />
              </button>
              <button type="button" onClick={() => { onClose(); onOpenSettings(); }} title="Settings" className="w-9 h-9 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors">
                <SettingsIcon className="w-5 h-5" />
              </button>
              <button type="button" onClick={onClose} className="w-9 h-9 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors" aria-label="Close">
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}


