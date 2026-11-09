'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic, MicOff, X, Volume2, VolumeX, Sparkles, Sliders, Send,
  Smartphone, Laptop, Server, HardDrive, Brain, Zap, Shield,
  Link2, Menu, Maximize2, Minimize2, MapPin, Navigation,
  Compass, Ruler, Search, Settings, Sun, Moon, ChevronDown,
  ChevronUp, Plus, X as XIcon, Copy, Check, AlertTriangle,
  Wifi, WifiOff, Battery, BatteryCharging, Clock, RotateCcw,
  Play, Pause, Star, Sparkle, Globe, Target, Route, Map,
  Layers, Cpu, Database, ShieldAlert, RefreshCw, Terminal,
  Code, Eye, EyeOff, Download, Upload, Trash2, Edit, FileText,
  Image, Video, Music, File, Folder, Search as SearchIcon,
  Filter, Grid, List, Home, User, Bell, Mail, Heart, Share2,
  ExternalLink, Download as DownloadIcon, Settings as SettingsIcon,
} from 'lucide-react';
import { useSyncExternalStore } from 'react';
import { THEME_CONFIGS, applyTheme } from '@/lib/theme';
import { AssistantSettings, DeviceState, AssistantTheme, ChatMessage, DeviceState as DeviceStateType } from '@/lib/types';
import { sounds, speakText, stopSpeaking } from '@/lib/audio';
import { HolographicAvatar } from '@/components/HolographicAvatar';
import { DeviceControlPanel } from '@/components/DeviceControlPanel';
import { SettingsModal } from '@/components/SettingsModal';
import { WorkspacesDrawer } from '@/components/WorkspacesDrawer';
import { ScreenContextSimulator } from '@/components/ScreenContextSimulator';
import { AskWithStellaMenu } from '@/components/AskWithStellaMenu';
import { DeviceLinkModal } from '@/components/DeviceLinkModal';
import { OnboardingModal } from '@/components/OnboardingModal';
import { BatteryIndicator } from '@/components/BatteryIndicator';
import { LocalGgufSelector } from '@/components/LocalGgufSelector';
import { StarSpinner } from '@/components/StarSpinner';
import dynamic from 'next/dynamic';

const LocationMapsModal = dynamic(() => import('@/components/LocationMapsModal'), {
  ssr: false,
  loading: () => <div className="fixed inset-0 flex items-center justify-center bg-[var(--stella-bg)]"><StarSpinner size={64} thickness={3} speed={1} /></div>,
});

const emptySubscribe = () => () => {};

const INITIAL_PROMPT_SUGGESTIONS = [
  { icon: 'ðŸ’¬', text: 'Hello Stella, what can you help me with?' },
  { icon: 'âš¡', text: 'Turn on flashlight and set device volume to 80%' },
  { icon: 'â°', text: 'Set a 15-minute timer for my focus session' },
  { icon: 'âœ‰ï¸', text: 'Draft a concise update about our on-device AI assistant launch' },
];

const STAR_DEFAULT = 'solar';

function useLocalStorage(key: string, initialValue: any) {
  const getSnapshot = () => {
    try {
      return (localStorage.getItem(key) as any) || initialValue;
    } catch {
      return initialValue;
    }
  };
  return useSyncExternalStore(
    () => () => {},
    getSnapshot,
    () => initialValue
  );
}

const DEFAULT_SETTINGS: AssistantSettings = {
  isDefaultAssistant: false,
  startListeningOnOpen: true,
  attachScreenshotOnInvoke: true,
  wakeWordEnabled: true,
  wakeWordPhrase: 'hey stella',
  contextAwarenessEnabled: true,
  theme: 'solar',
  animateBackground: true,
  voicePitch: 1,
  voiceRate: 1,
  autoSpeakResponse: true,
  autoRespondOnPause: true,
  pauseThresholdMs: 1500,
  soundEffects: true,
  hapticFeedback: true,
};

function FeatureCard({ icon, title, description, iconColor }: { icon: React.ReactNode; title: string; description: string; iconColor: string }) {
  return (
    <div className="card card-hover p-6 flex flex-col gap-4">
      <div className="p-3 rounded-xl" style={{ background: iconColor + '15', border: '1px solid ' + iconColor + '30' }}>
        <span style={{ color: iconColor }}>{icon}</span>
      </div>
      <div>
        <h3 className="font-semibold text-lg mb-1" style={{ color: 'var(--stella-text-primary)' }}>{title}</h3>
        <p className="text-sm" style={{ color: 'var(--stella-text-secondary)' }}>{description}</p>
      </div>
    </div>
  );
}

export default function Page() {
  const [settings, setSettings] = useLocalStorage('assistant-settings', DEFAULT_SETTINGS);
  const [theme, setTheme] = useState<AssistantTheme>(settings.theme);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isWorkspacesOpen, setIsWorkspacesOpen] = useState(false);
  const [isScreenContextOpen, setIsScreenContextOpen] = useState(false);
  const [isDeviceLinkOpen, setIsDeviceLinkOpen] = useState(false);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);
  const [isMapsOpen, setIsMapsOpen] = useState(false);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  return (
    <div className="fixed inset-0 bg-[var(--stella-bg)] text-[var(--stella-text-primary)] flex flex-col">
      <HolographicAvatar isListening isSpeaking isThinking />
      <DeviceControlPanel deviceState={{} as DeviceState} onUpdateState={() => {}} />
      <BatteryIndicator />
      <StarSpinner size={64} thickness={3} speed={1} />

      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} settings={settings} />
      <WorkspacesDrawer isOpen={isWorkspacesOpen} onClose={() => setIsWorkspacesOpen(false)} />
      <ScreenContextSimulator isOpen={isScreenContextOpen} onClose={() => setIsScreenContextOpen(false)} onAttachContext={() => {}} />
      <AskWithStellaMenu enabled onAsk={() => {}} />
      <DeviceLinkModal isOpen={isDeviceLinkOpen} onClose={() => setIsDeviceLinkOpen(false)} />
      <OnboardingModal isOpen={isOnboardingOpen} onClose={() => setIsOnboardingOpen(false)} onComplete={() => {}} />
      <LocalGgufSelector />
      <LocationMapsModal isOpen={isMapsOpen} onClose={() => setIsMapsOpen(false)} theme={theme} />

      <main className="flex-1 p-8 flex flex-col items-center justify-center gap-4">
        <h1 className="text-4xl font-bold">Stella</h1>
        <p className="text-lg text-[var(--stella-text-secondary)]">Your on-device AI assistant</p>
        <div className="grid grid-cols-2 gap-4 mt-8">
          <FeatureCard icon={<Zap className="w-8 h-8" />} title="Fast &amp; Local" description="Runs entirely on your device with no cloud dependency." iconColor="text-emerald-400" />
          <FeatureCard icon={<Shield className="w-8 h-8" />} title="Private &amp; Secure" description="Your data never leaves your machine." iconColor="text-blue-400" />
          <FeatureCard icon={<Star className="w-8 h-8" />} title="Holographic UI" description="Futuristic interface with voice and visual feedback." iconColor="text-purple-400" />
          <FeatureCard icon={<Map className="w-8 h-8" />} title="Location &amp; Maps" description="Integrated maps with satellite, terrain, and hybrid layers." iconColor="text-cyan-400" />
        </div>
      </main>
    </div>
  );
}


