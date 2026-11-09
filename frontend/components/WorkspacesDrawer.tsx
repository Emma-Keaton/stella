'use client';

import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  X,
  Clock,
  Settings as SettingsIcon,
  Plus,
  QrCode,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  Sparkles,
  Smartphone,
  Trash2,
} from 'lucide-react';
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
  const [deviceChatsOpen, setDeviceChatsOpen] = React.useState(true);
  const [showWorkspaceDropdown, setShowWorkspaceDropdown] = React.useState(false);

  const currentWorkspace =
    workspaces.find((w) => w.id === activeWorkspaceId) || workspaces[0];

  const standardThreads = currentWorkspace?.threads.filter(
    (t) => !t.isDeviceAssistantChat
  ) || [];
  const deviceAssistantThreads = currentWorkspace?.threads.filter(
    (t) => t.isDeviceAssistantChat
  ) || [];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />

          {/* Drawer Sheet */}
          <motion.aside
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 26, stiffness: 260 }}
            className="fixed top-0 bottom-0 left-0 z-50 w-full max-w-xs sm:max-w-sm bg-[#101216] text-white border-r border-slate-800/80 flex flex-col shadow-2xl"
          >
            {/* Header: Workspaces, Clock, Settings */}
            <div className="flex items-center justify-between px-5 pt-6 pb-4 border-b border-slate-800/60">
              <h2 className="text-xl font-medium tracking-tight text-white/95">
                Workspaces
              </h2>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    /* quick history alert or scroll */
                  }}
                  title="Chat history"
                  className="w-9 h-9 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
                >
                  <Clock className="w-5 h-5" />
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onOpenSettings();
                  }}
                  title="Settings"
                  className="w-9 h-9 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
                >
                  <SettingsIcon className="w-5 h-5" />
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="w-9 h-9 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors md:hidden"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Workspace Selector */}
            <div className="p-4">
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowWorkspaceDropdown(!showWorkspaceDropdown)}
                  className="w-full flex items-center justify-between px-3.5 py-3 rounded-xl bg-[#181a20] hover:bg-[#1e2028] border border-slate-800 transition-colors text-left"
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <div className="w-6 h-6 rounded-md bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                      <Sparkles className="w-3.5 h-3.5" />
                    </div>
                    <span className="font-medium text-sm text-slate-100 truncate">
                      {currentWorkspace?.name || 'My Workspace'}
                    </span>
                  </div>
                  <ChevronDown
                    className={`w-4 h-4 text-slate-400 transition-transform ${
                      showWorkspaceDropdown ? 'rotate-180' : ''
                    }`}
                  />
                </button>

                {showWorkspaceDropdown && (
                  <div className="absolute top-full left-0 right-0 mt-1.5 p-1 bg-[#1c1e24] border border-slate-700/80 rounded-xl shadow-xl z-20 space-y-0.5">
                    {workspaces.map((ws) => (
                      <button
                        key={ws.id}
                        type="button"
                        onClick={() => {
                          onSelectWorkspace(ws.id);
                          setShowWorkspaceDropdown(false);
                        }}
                        className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-lg transition-colors text-left ${
                          ws.id === activeWorkspaceId
                            ? 'bg-cyan-500/20 text-cyan-300 font-medium'
                            : 'text-slate-300 hover:bg-slate-800'
                        }`}
                      >
                        <span className="truncate">{ws.name}</span>
                        <span className="text-[10px] text-slate-500">
                          {ws.threads.length} threads
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Content List */}
            <div className="flex-1 overflow-y-auto px-4 space-y-4">
              {/* New Thread CTA */}
              <button
                type="button"
                onClick={() => {
                  onNewThread(false);
                  onClose();
                }}
                className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-slate-300 hover:text-white hover:bg-[#181a20] transition-colors text-sm font-medium"
              >
                <Plus className="w-4 h-4 text-cyan-400" />
                <span>New Thread</span>
              </button>

              {/* Standard Threads List */}
              {standardThreads.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[11px] font-semibold tracking-wider text-slate-400 px-3 uppercase">
                    Conversations
                  </span>
                  {standardThreads.map((thread) => (
                    <div
                      key={thread.id}
                      className={`group flex items-center justify-between px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer ${
                        thread.id === activeThreadId
                          ? 'bg-slate-800 text-white font-medium'
                          : 'text-slate-300 hover:bg-[#181a20] hover:text-white'
                      }`}
                      onClick={() => {
                        onSelectThread(thread.id);
                        onClose();
                      }}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <MessageSquare className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span className="truncate">{thread.title}</span>
                      </div>
                      {onDeleteThread && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteThread(thread.id);
                          }}
                          className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-400 transition-opacity"
                          title="Delete thread"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Device Assistant Chats (Collapsible Section as in screenshot) */}
              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => setDeviceChatsOpen(!deviceChatsOpen)}
                  className="w-full flex items-center justify-between px-3 py-2 text-slate-300 hover:text-white transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <Smartphone className="w-4 h-4 text-cyan-400" />
                    <span className="text-sm font-medium">Device Assistant Chats</span>
                  </div>
                  {deviceChatsOpen ? (
                    <ChevronDown className="w-4 h-4 text-slate-500" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-slate-500" />
                  )}
                </button>

                {deviceChatsOpen && (
                  <div className="mt-1 pl-4 space-y-1">
                    <button
                      type="button"
                      onClick={() => {
                        onNewThread(true);
                        onClose();
                      }}
                      className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-cyan-300 hover:bg-[#181a20] transition-colors"
                    >
                      <Plus className="w-3.5 h-3.5 text-cyan-400" />
                      <span>New Device Session</span>
                    </button>

                    {deviceAssistantThreads.length === 0 ? (
                      <p className="px-3 py-2 text-[11px] text-slate-400 italic">
                        No voice assistant logs yet
                      </p>
                    ) : (
                      deviceAssistantThreads.map((thread) => (
                        <div
                          key={thread.id}
                          className={`group flex items-center justify-between px-3 py-2 rounded-lg text-xs transition-colors cursor-pointer ${
                            thread.id === activeThreadId
                              ? 'bg-slate-800 text-cyan-300 font-medium'
                              : 'text-slate-300 hover:bg-[#181a20] hover:text-white'
                          }`}
                          onClick={() => {
                            onSelectThread(thread.id);
                            onClose();
                          }}
                        >
                          <div className="flex items-center gap-2 truncate">
                            <Sparkles className="w-3 h-3 text-cyan-400 shrink-0" />
                            <span className="truncate">{thread.title}</span>
                          </div>
                          {onDeleteThread && (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                onDeleteThread(thread.id);
                              }}
                              className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-400 transition-opacity"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Bottom Section: New Workspace + QR / Device connect */}
            <div className="p-4 border-t border-slate-800/80 flex items-center gap-2">
              <button
                type="button"
                onClick={onNewWorkspace}
                className="flex-1 py-3 px-4 rounded-xl bg-[#1c1e24] hover:bg-[#252830] border border-slate-700/60 text-white font-medium text-sm transition-colors flex items-center justify-center gap-2"
              >
                <Plus className="w-4 h-4" />
                <span>New Workspace</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  alert('Device Sync QR: Scan to connect Stella with your companion phone or tablet.');
                }}
                title="Scan QR Code"
                className="w-12 h-12 rounded-xl bg-[#1c1e24] hover:bg-[#252830] border border-slate-700/60 text-slate-300 hover:text-white flex items-center justify-center transition-colors shrink-0"
              >
                <QrCode className="w-5 h-5" />
              </button>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
