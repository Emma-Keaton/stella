'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  ArrowLeft,
  Sparkles,
  Smartphone,
  Type,
  Github,
  MessageCircle,
  FileText,
  Globe,
  ShieldCheck,
  Trash2,
  ChevronRight,
  Volume2,
  Mic,
  Sliders,
  Check,
  Key,
  Eye,
  EyeOff,
  AlertTriangle,
  CheckCircle2,
  Share2,
  HelpCircle,
  Save,
  Cpu,
  Layers,
  Palette,
  HardDrive,
  Sun,
} from 'lucide-react';
import { AssistantSettings, AssistantTheme, ModelOption, ProviderType, LocalGgufModel, TTSVoice, TTSProviderType } from '@/lib/types';
import { THEME_CONFIGS } from '@/lib/theme';
import { StarSpinner } from './StarSpinner';
import { LocalGgufSelector } from './LocalGgufSelector';
import { stellaWS, createWSMessage } from '@/lib/websocket';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AssistantSettings;
  onUpdateSettings: (newSettings: Partial<AssistantSettings>) => void;
  onOpenDeviceAssistant: () => void;
  onOpenDeviceLink: () => void;
  onReplayOnboarding: () => void;
  onClearHistory: () => void;
  activeProvider: ProviderType;
  onChangeProvider: (provider: ProviderType) => void;
  activeModel: string;
  onChangeModel: (model: string) => void;
  localGgufModel: LocalGgufModel | null;
  onSelectLocalGgufModel: (model: LocalGgufModel) => void;
  onProviderConfigured: () => void;
  onModelDeauthorized: () => void;
  ttsVoices: TTSVoice[];
  onChangeTtsVoice: (voiceId: string) => void;
  onChangeTtsProvider: (provider: TTSProviderType) => void;
}

export function SettingsModal({
  isOpen,
  onClose,
  settings,
  onUpdateSettings,
  onOpenDeviceAssistant,
  onOpenDeviceLink,
  onReplayOnboarding,
  onClearHistory,
  activeProvider,
  onChangeProvider,
  activeModel,
  onChangeModel,
  localGgufModel,
  onSelectLocalGgufModel,
  onProviderConfigured,
  onModelDeauthorized,
  ttsVoices,
  onChangeTtsVoice,
  onChangeTtsProvider,
}: SettingsModalProps) {
  const themeConfig = THEME_CONFIGS[settings.theme] || THEME_CONFIGS.void;

  // Provider & API Key State
  const [selectedProvider, setSelectedProvider] = useState<ProviderType>(activeProvider || 'gemini');
  const [apiKeys, setApiKeys] = useState<Record<ProviderType, string>>({
    gemini: '',
    nvidia: '',
    openrouter: '',
    openai: '',
    groq: '',
    anthropic: '',
    google_maps: '',
    local_gguf: '',
  });
  const [keysLoaded, setKeysLoaded] = useState(false);
  const [showKey, setShowKey] = useState(false);

  // Key Tester State
  const [isTestingKey, setIsTestingKey] = useState(false);
  const [testResult, setTestResult] = useState<{
    valid: boolean;
    authLevel?: string;
    error?: string;
    fixSuggestion?: string;
  } | null>(null);

  // Available Models verified for current provider — populated only after API key is tested
  // and the provider returns its authorized model list. No hardcoded model names.
  const [availableModels, setAvailableModels] = useState<ModelOption[]>([]);

  const [modelSelectorOpen, setModelSelectorOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2500);
  };

  // ── Device Controls (wired to backend WebSocket) ──
  const [deviceControls, setDeviceControls] = useState<{ volume: number; brightness: number }>({
    volume: 70,
    brightness: 85,
  });
  const [deviceControlStatus, setDeviceControlStatus] = useState<string | null>(null);

  const sendDeviceCommand = async (command: string, payload: any) => {
    setDeviceControlStatus('sending…');
    try {
      const res = await stellaWS.request(
        createWSMessage('device.command', { command, payload }),
        15000
      );
      setDeviceControlStatus(res?.ok ? 'applied' : (res?.error || 'failed'));
      setTimeout(() => setDeviceControlStatus(null), 1500);
      return res;
    } catch (err) {
      setDeviceControlStatus('error');
      setTimeout(() => setDeviceControlStatus(null), 1500);
      console.warn('[Stella Settings] device.command failed:', err);
    }
  };

  // ── Load all provider keys from backend on mount ──
  useEffect(() => {
    let cancelled = false;
    const loadKeys = async () => {
      try {
        const res = await fetch('/api/stella/config/api-keys');
        if (res.ok) {
          const data = await res.json();
          if (data.keys) {
            setApiKeys(data.keys);
          }
          setKeysLoaded(data.configured ?? false);
        }
      } catch {
        // Backend config not available yet; keys remain empty.
      }
    };
    loadKeys();
    return () => { cancelled = true; };
  }, []);

  // ── Persist all provider keys to backend ──
  const handleSaveKeys = async () => {
    try {
      const res = await fetch('/api/stella/config/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keys: apiKeys }),
      });
      if (res.ok) {
        const data = await res.json();
        setKeysLoaded(data.configured ?? false);
        showToast('API keys saved to backend config.');
      } else {
        showToast('Failed to save API keys to backend.');
      }
    } catch {
      showToast('Failed to save API keys to backend.');
    }
  };

  const providers: Array<{
    id: ProviderType;
    name: string;
    badge: string;
    keyPrefix: string;
    docsUrl: string;
    description: string;
  }> = [
    {
      id: 'gemini',
      name: 'Google Gemini',
      badge: 'Native Audio & Vision',
      keyPrefix: 'AIzaSy...',
      docsUrl: 'aistudio.google.com',
      description: 'Ultra low latency multimodal model with direct token streaming.',
    },
    {
      id: 'nvidia',
      name: 'NVIDIA',
      badge: 'Popular • Enterprise AI',
      keyPrefix: 'nvapi-...',
      docsUrl: 'build.nvidia.com',
      description: 'Nemotron-4 340B & 70B models accelerated on NVIDIA HGX clusters.',
    },
    {
      id: 'openrouter',
      name: 'OpenRouter',
      badge: 'Multi-Model Hub',
      keyPrefix: 'sk-or-v1-...',
      docsUrl: 'openrouter.ai/keys',
      description: 'Access Nemotron 3.5, Claude 3.5 Sonnet, and DeepSeek R1.',
    },
    {
      id: 'openai',
      name: 'OpenAI',
      badge: 'GPT-4o & Reasoning',
      keyPrefix: 'sk-...',
      docsUrl: 'platform.openai.com',
      description: 'GPT-4o Omni audio & text with o1 deliberation reasoning.',
    },
    {
      id: 'groq',
      name: 'Groq Cloud',
      badge: '800 Tokens/Sec',
      keyPrefix: 'gsk_...',
      docsUrl: 'console.groq.com',
      description: 'LPU Inference Engine for lightning-fast voice turnaround.',
    },
    {
      id: 'anthropic',
      name: 'Anthropic',
      badge: 'Claude 3.7',
      keyPrefix: 'sk-ant-...',
      docsUrl: 'console.anthropic.com',
      description: 'Claude 3.7 Sonnet hybrid reasoning & coding intelligence.',
    },
    {
      id: 'google_maps',
      name: 'Google Maps',
      badge: 'Places • Routes • Distance',
      keyPrefix: 'AIza...',
      docsUrl: 'console.cloud.google.com',
      description: 'Enable maps, directions, distance measurement, and nearby search actions.',
    },
  ];

  // Test API Key against server verification route
  const handleTestKey = async () => {
    setIsTestingKey(true);
    setTestResult(null);

    try {
      const res = await fetch('/api/stella/providers/test-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: selectedProvider,
          apiKey: apiKeys[selectedProvider] || '',
        }),
      });

      const data = await res.json();

      if (data.valid) {
        setTestResult({
          valid: true,
          authLevel: data.authLevel,
        });
        if (data.models && data.models.length > 0) {
          setAvailableModels(data.models);
          // Set active model to first available if current model not in list
          if (!data.models.some((m: ModelOption) => m.id === activeModel || m.name === activeModel)) {
            onChangeModel(data.models[0].name);
          }
        }
        onChangeProvider(selectedProvider);
        onProviderConfigured();
        showToast(`Key verified! ${data.models?.length || 0} models unlocked.`);
      } else {
        setTestResult({
          valid: false,
          error: data.error || 'Authorization Failed',
          fixSuggestion: data.fixSuggestion || 'Please verify that your API key is accurate.',
        });
        onModelDeauthorized();
      }
    } catch (err) {
      setTestResult({
        valid: false,
        error: 'Network Verification Error',
        fixSuggestion: 'Unable to reach the provider testing endpoint. Please check your internet connection.',
      });
    } finally {
      setIsTestingKey(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 20 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-50 bg-[#0c0e12] text-slate-100 overflow-y-auto"
        >
          {/* Top Bar with theme accent */}
          <div className="sticky top-0 z-20 bg-[#0c0e12]/90 backdrop-blur-md px-4 py-4 border-b border-slate-800/80 flex items-center justify-between max-w-2xl mx-auto">
            <button
              type="button"
              onClick={onClose}
              className="p-2 -ml-2 rounded-full hover:bg-slate-800/80 text-slate-300 hover:text-white transition-colors"
              aria-label="Back"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <StarSpinner size="xs" theme={settings.theme} />
              <h1 className="text-base font-semibold text-white tracking-tight">Settings</h1>
            </div>
            <div className="w-9" />
          </div>

          <div className="max-w-2xl mx-auto px-4 py-6 space-y-7 pb-24">
            {/* THEME SELECTION - AFFECTS ENTIRE APP */}
            <div className="space-y-2">
              <div className="flex items-center justify-between px-1">
                <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
                  App Visual Theme
                </span>
                <span
                  className="text-xs font-semibold uppercase tracking-wider font-mono"
                  style={{ color: themeConfig.primaryHex }}
                >
                  {themeConfig.name}
                </span>
              </div>

              <div className="rounded-2xl bg-[#14161d] border border-slate-800 p-4 space-y-3">
                <p className="text-xs text-slate-400">
                  Select your neon theme palette. Changes apply across the entire app interface: accents, glows, buttons, borders, and animations.
                </p>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  {(['void', 'oled', 'aurora', 'light', 'solar'] as AssistantTheme[]).map((thm) => {
                    const cfg = THEME_CONFIGS[thm];
                    const isSelected = settings.theme === thm;
                    return (
                      <button
                        key={thm}
                        type="button"
                        onClick={() => {
                          onUpdateSettings({ theme: thm });
                          showToast(`Theme changed to ${cfg.name}`);
                        }}
                        className={`p-3 rounded-xl border text-left transition-all relative ${
                          isSelected
                            ? 'border-white/80 shadow-lg'
                            : 'border-slate-800 bg-[#0e1017] hover:border-slate-700'
                        }`}
                        style={{
                          background: isSelected
                            ? `linear-gradient(135deg, ${cfg.primaryHex}25 0%, #10131c 100%)`
                            : undefined,
                          borderColor: isSelected ? cfg.primaryHex : undefined,
                        }}
                      >
                        <div className="flex items-center gap-2 mb-1.5">
                          <div
                            className="w-3.5 h-3.5 rounded-full shadow"
                            style={{ backgroundColor: cfg.primaryHex }}
                          />
                          <span className="text-xs font-bold text-white capitalize">{thm}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          {cfg.gradientStops.map((c, i) => (
                            <span
                              key={i}
                              className="w-2.5 h-1 rounded-full"
                              style={{ backgroundColor: c }}
                            />
                          ))}
                        </div>
                        {isSelected && (
                          <div
                            className="absolute top-2 right-2 w-4 h-4 rounded-full flex items-center justify-center text-black font-bold"
                            style={{ backgroundColor: cfg.primaryHex }}
                          >
                            <Check className="w-2.5 h-2.5" />
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* LLM PROVIDER & MODEL SELECTOR */}
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
                  LLM Provider & Model Preference
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                  Key Verification Engine
                </span>
              </div>

              <div className="rounded-2xl bg-[#14161d] border border-slate-800 p-5 space-y-5">
                {/* 1. Provider Selector */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300">
                    Select AI Provider
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {providers.map((p) => {
                      const isSelected = selectedProvider === p.id;
                      return (
                        <button
                          key={p.id}
                          type="button"
                          onClick={() => {
                            setSelectedProvider(p.id);
                            setTestResult(null);
                            onModelDeauthorized();
                          }}
                          className={`p-3 rounded-xl border text-left transition-all ${
                            isSelected
                              ? 'bg-cyan-950/40 border-cyan-400/80 text-white shadow-md'
                              : 'bg-[#10121a] border-slate-800 text-slate-400 hover:border-slate-700'
                          }`}
                          style={{
                            borderColor: isSelected ? themeConfig.primaryHex : undefined,
                            background: isSelected
                              ? `${themeConfig.primaryHex}15`
                              : undefined,
                          }}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-white truncate">{p.name}</span>
                            {isSelected && (
                              <Check
                                className="w-3.5 h-3.5 shrink-0"
                                style={{ color: themeConfig.primaryHex }}
                              />
                            )}
                          </div>
                          <span className="text-[10px] text-slate-400 block truncate mt-0.5">
                            {p.badge}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* 2. API Key Input Section with Key Tester */}
                <div className="p-4 rounded-xl bg-[#0e1017] border border-slate-800/90 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                      <Key className="w-3.5 h-3.5" style={{ color: themeConfig.primaryHex }} />
                      <span>{providers.find((p) => p.id === selectedProvider)?.name} API Key</span>
                    </span>
                    <span className="text-[11px] text-slate-500 font-mono">
                      Format: {providers.find((p) => p.id === selectedProvider)?.keyPrefix}
                    </span>
                  </div>

                  <div className="relative">
                    <input
                      type={showKey ? 'text' : 'password'}
                      placeholder={
                        selectedProvider === 'nvidia'
                          ? 'Paste NVIDIA API key (nvapi-...)'
                          : selectedProvider === 'gemini'
                          ? 'Paste Google AI Studio key or leave empty for default'
                          : selectedProvider === 'google_maps'
                          ? 'Paste Google Maps API key (AIza...)'
                          : `Paste ${selectedProvider} API key`
                      }
                      value={apiKeys[selectedProvider]}
                      onChange={(e) => {
                        setApiKeys({
                          ...apiKeys,
                          [selectedProvider]: e.target.value,
                        });
                        setTestResult(null);
                      }}
                      className="w-full px-3.5 py-2.5 pr-20 rounded-xl bg-[#151824] border border-slate-700 text-white font-mono text-xs placeholder:text-slate-600 focus:outline-none"
                      style={{
                        borderColor: apiKeys[selectedProvider] ? themeConfig.primaryHex : undefined,
                      }}
                    />
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setShowKey(!showKey)}
                        className="p-1.5 text-slate-400 hover:text-white transition-colors"
                        title={showKey ? 'Hide key' : 'Show key'}
                      >
                        {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  {/* Test Key CTA Button */}
                  <div className="flex items-center justify-between gap-3 pt-1">
                    <p className="text-[11px] text-slate-500">
                      Keys are tested directly against authorization endpoints to unlock active models.
                    </p>

                    <button
                      type="button"
                      onClick={handleTestKey}
                      disabled={isTestingKey}
                      className={`px-4 py-2 rounded-xl text-white font-semibold text-xs shrink-0 flex items-center gap-2 transition-transform active:scale-95 ${themeConfig.buttonGradient} ${themeConfig.buttonShadow}`}
                    >
                      {isTestingKey ? (
                        <>
                          <StarSpinner size="xs" theme={settings.theme} />
                          <span>Testing...</span>
                        </>
                      ) : (
                        <>
                          <ShieldCheck className="w-3.5 h-3.5" />
                          <span>Test & Authorize</span>
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={handleSaveKeys}
                      disabled={isTestingKey}
                      className={`px-4 py-2 rounded-xl text-white font-semibold text-xs shrink-0 flex items-center gap-2 transition-transform active:scale-95 bg-slate-700 hover:bg-slate-600 border border-slate-600`}
                    >
                      <Save className="w-3.5 h-3.5" />
                      <span>Save to Backend</span>
                    </button>
                  </div>

                  {/* Friendly Human Error / Success Feedback Box */}
                  {testResult && (
                    <motion.div
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`p-3.5 rounded-xl border text-xs space-y-1.5 ${
                        testResult.valid
                          ? 'bg-emerald-950/40 border-emerald-600/70 text-emerald-300'
                          : 'bg-rose-950/40 border-rose-600/70 text-rose-300'
                      }`}
                    >
                      <div className="flex items-center gap-2 font-semibold">
                        {testResult.valid ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                        )}
                        <span>
                          {testResult.valid
                            ? testResult.authLevel || 'API Key Verified & Authorized'
                            : testResult.error}
                        </span>
                      </div>

                      {testResult.fixSuggestion && (
                        <p className="text-[11px] text-slate-300 pl-6 leading-relaxed">
                          <strong className="text-white">How to fix: </strong>
                          {testResult.fixSuggestion}
                        </p>
                      )}
                    </motion.div>
                  )}
                </div>

                {/* 3. Verified Accessible Models Selector */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-semibold text-slate-300">
                      Accessible Models for {providers.find((p) => p.id === selectedProvider)?.name}
                    </label>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {availableModels.length} Authorized
                    </span>
                  </div>

                  <div className="space-y-2">
                    {availableModels.map((m) => {
                      const isSelected = activeModel === m.name || activeModel === m.id;
                      return (
                        <button
                          key={m.id}
                          type="button"
                          onClick={() => {
                            onChangeModel(m.name);
                            if (m.isAuthorized) {
                              onProviderConfigured();
                            }
                            showToast(`Active model switched to ${m.name}`);
                          }}
                          className={`w-full text-left p-3 rounded-xl border transition-all flex items-start justify-between ${
                            isSelected
                              ? 'bg-cyan-950/40 border-cyan-400/80 shadow'
                              : 'bg-[#10121a] border-slate-800 hover:border-slate-700'
                          }`}
                          style={{
                            borderColor: isSelected ? themeConfig.primaryHex : undefined,
                            background: isSelected
                              ? `${themeConfig.primaryHex}15`
                              : undefined,
                          }}
                        >
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-white">{m.name}</span>
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                                {m.tier}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-400 leading-snug">{m.description}</p>
                            {m.contextWindow && (
                              <span className="text-[10px] text-slate-500 font-mono">
                                Context: {m.contextWindow}
                              </span>
                            )}
                          </div>

                          {isSelected && (
                            <Check
                              className="w-4 h-4 shrink-0 mt-0.5"
                              style={{ color: themeConfig.primaryHex }}
                            />
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>

            {/* ON-DEVICE LOCAL MODEL (GGUF) SELECTOR - Directly under Cloud Provider Config */}
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
                  On-Device Local Model (GGUF)
                </span>
                <span
                  className="text-[10px] font-mono px-2 py-0.5 rounded-full border"
                  style={{
                    color: themeConfig.primaryHex,
                    borderColor: themeConfig.primaryHex + '40',
                    background: themeConfig.primaryHex + '15',
                  }}
                >
                  Zero Cloud &bull; 100% Private
                </span>
              </div>

              <div className="rounded-2xl bg-[#14161d] border border-slate-800 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-white">Serve Local Model File (.gguf)</h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Select or drop any local quantized GGUF file to run private on-device neural serving.
                    </p>
                  </div>
                  {activeProvider === 'local_gguf' && (
                    <span
                      className="text-xs font-semibold px-2.5 py-1 rounded-full border flex items-center gap-1 shrink-0"
                      style={{
                        color: themeConfig.primaryHex,
                        borderColor: themeConfig.primaryHex + '40',
                        background: themeConfig.primaryHex + '15',
                      }}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Active Serving
                    </span>
                  )}
                </div>

                <LocalGgufSelector
                  currentModel={localGgufModel}
                  onSelectModel={(model) => {
                    onSelectLocalGgufModel(model);
                    onChangeProvider('local_gguf');
                    onChangeModel(`[Local GGUF] ${model.fileName}`);
                    onProviderConfigured();
                    showToast(`Local model ${model.fileName} is now active on Stella!`);
                  }}
                  theme={settings.theme}
                />
              </div>
            </div>

            {/* DEVICE LINK HUB CTA */}
            <div className="space-y-2">
              <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase px-1">
                Multi-Device Mesh
              </span>

              <div className="rounded-2xl bg-[#14161d] border border-slate-800 p-4">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onOpenDeviceLink();
                  }}
                  className="w-full flex items-center justify-between text-left hover:opacity-90 transition-opacity"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-9 h-9 rounded-xl flex items-center justify-center border"
                      style={{
                        borderColor: themeConfig.primaryHex + '50',
                        color: themeConfig.primaryHex,
                        background: themeConfig.primaryHex + '15',
                      }}
                    >
                      <Share2 className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-white">Device Link Hub</h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Cross-connect Stella across up to 5 devices &bull; Defer heavy tasks to PCs
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </button>
              {/* Device Controls: volume & brightness sliders wired to WebSocket */}
              <div className="rounded-2xl bg-[#14161d] border border-slate-800 p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase px-1">
                    Device Controls
                  </span>
                  {deviceControlStatus && (
                    <span className={deviceControlStatus === 'applied' ? 'text-[10px] font-mono px-2 py-0.5 rounded border border-emerald-500/50 bg-emerald-500/10 text-emerald-400' : 'text-[10px] font-mono px-2 py-0.5 rounded border border-rose-500/50 bg-rose-500/10 text-rose-400'}>
                      {deviceControlStatus}
                    </span>
                  )}
                </div>
                <div className="space-y-3">
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1.5 text-slate-300">
                        <Volume2 className="w-4 h-4 text-cyan-400" />
                        <span>Volume</span>
                      </div>
                      <span className="text-slate-400 font-mono">{deviceControls.volume}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={deviceControls.volume}
                      onChange={(e) => {
                        const val = parseInt(e.target.value);
                        setDeviceControls((prev) => ({ ...prev, volume: val }));
                        sendDeviceCommand('volume', { level: val });
                      }}
                      className="w-full h-1.5 bg-slate-700 rounded-lg accent-cyan-400 cursor-pointer"
                    />
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1.5 text-slate-300">
                        <Sun className="w-4 h-4 text-amber-400" />
                        <span>Brightness</span>
                      </div>
                      <span className="text-slate-400 font-mono">{deviceControls.brightness}%</span>
                    </div>
                    <input
                      type="range"
                      min="10"
                      max="100"
                      value={deviceControls.brightness}
                      onChange={(e) => {
                        const val = parseInt(e.target.value);
                        setDeviceControls((prev) => ({ ...prev, brightness: val }));
                        sendDeviceCommand('brightness', { level: val });
                      }}
                      className="w-full h-1.5 bg-slate-700 rounded-lg accent-amber-400 cursor-pointer"
                    />
                  </div>
                  <p className="text-[10px] text-slate-500">
                    Sliders send commands to the device over Stella's local WebSocket.
                  </p>
                </div>
              </div>

              </div>
            </div>

            {/* SPECIAL TOOLS */}
            <div className="space-y-2">
              <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase px-1">
                Special Tools
              </span>

              <div className="rounded-2xl bg-[#14161d] border border-slate-800 divide-y divide-slate-800/80 overflow-hidden">
                {/* Device Assistant link */}
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onOpenDeviceAssistant();
                  }}
                  className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-800/40 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Sparkles className="w-5 h-5 shrink-0" style={{ color: themeConfig.primaryHex }} />
                    <div>
                      <h3 className="text-sm font-medium text-white">Device Assistant</h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {settings.isDefaultAssistant
                          ? 'Active as default assistant • Voice & hardware control'
                          : 'Configure Stella as default digital assistant'}
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </button>

                {/* Ask with Stella (Context awareness) */}
                <div className="p-4 flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <Type className="w-5 h-5 mt-0.5 shrink-0" style={{ color: themeConfig.primaryHex }} />
                    <div>
                      <h3 className="text-sm font-medium text-white">&ldquo;Ask with Stella&rdquo;</h3>
                      <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                        Adds &ldquo;Ask with Stella&rdquo; to the menu that appears when you select text in any app. Use it to polish, shorten, summarize, or research text.
                      </p>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer shrink-0 mt-0.5">
                    <input
                      type="checkbox"
                      checked={settings.contextAwarenessEnabled}
                      onChange={(e) =>
                        onUpdateSettings({ contextAwarenessEnabled: e.target.checked })
                      }
                      className="sr-only peer"
                    />
                    <div
                      className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all"
                      style={{
                        backgroundColor: settings.contextAwarenessEnabled
                          ? themeConfig.primaryHex
                          : undefined,
                      }}
                    />
                  </label>
                </div>
              </div>
            </div>

            {/* WAKE WORD CONFIGURATION */}
            <div className="space-y-2">
              <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase px-1">
                Wake Word Activation
              </span>

              <div className="rounded-2xl bg-[#14161d] border border-slate-800 divide-y divide-slate-800/80 overflow-hidden">
                <div className="p-4 flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <Mic className="w-5 h-5 mt-0.5 shrink-0" style={{ color: themeConfig.primaryHex }} />
                    <div>
                      <h3 className="text-sm font-medium text-white">Wake Word Engine</h3>
                      <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                        Allows waking Stella hands-free by saying &ldquo;Hey Stella&rdquo;, &ldquo;OK Stella&rdquo;, or &ldquo;Stella&rdquo;.
                      </p>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer shrink-0 mt-0.5">
                    <input
                      type="checkbox"
                      checked={settings.wakeWordEnabled}
                      onChange={(e) =>
                        onUpdateSettings({ wakeWordEnabled: e.target.checked })
                      }
                      className="sr-only peer"
                    />
                    <div
                      className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all"
                      style={{
                        backgroundColor: settings.wakeWordEnabled
                          ? themeConfig.primaryHex
                          : undefined,
                      }}
                    />
                  </label>
                </div>

                {settings.wakeWordEnabled && (
                  <div className="p-4 bg-[#101217] space-y-3 border-t border-slate-800/80">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between text-xs gap-1.5">
                      <span className="text-slate-300 font-medium">Accepted Wake Words:</span>
                      <div
                        className="px-2.5 py-1 rounded-lg border font-mono text-[11px] font-semibold flex items-center gap-1.5"
                        style={{
                          color: themeConfig.primaryHex,
                          borderColor: themeConfig.primaryHex + '40',
                          background: themeConfig.primaryHex + '12',
                        }}
                      >
                        <span>&ldquo;Hey Stella&rdquo;</span>
                        <span className="opacity-50">&bull;</span>
                        <span>&ldquo;OK Stella&rdquo;</span>
                        <span className="opacity-50">&bull;</span>
                        <span>&ldquo;Stella&rdquo;</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-300 font-medium">Auto-respond on user silence:</span>
                      <span
                        className="font-mono text-[11px] font-semibold"
                        style={{ color: themeConfig.secondaryHex }}
                      >
                        1.4s pause threshold
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* VOICE & SPEECH OUTPUT */}
            <div className="space-y-2">
              <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase px-1">
                Voice & Speech
              </span>

              <div className="rounded-2xl bg-[#14161d] border border-slate-800 divide-y divide-slate-800/80 overflow-hidden">
                <div className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Volume2 className="w-5 h-5 shrink-0" style={{ color: themeConfig.primaryHex }} />
                    <div>
                      <h3 className="text-sm font-medium text-white">Auto-speak Responses</h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Voice replies aloud with token-streamed speech
                      </p>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer shrink-0">
                    <input
                      type="checkbox"
                      checked={settings.autoSpeakResponse}
                      onChange={(e) =>
                        onUpdateSettings({ autoSpeakResponse: e.target.checked })
                      }
                      className="sr-only peer"
                    />
                    <div
                      className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all"
                      style={{
                        backgroundColor: settings.autoSpeakResponse
                          ? themeConfig.primaryHex
                          : undefined,
                      }}
                    />
                  </label>
                </div>

                <div className="p-4 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-medium">Speech Rate</span>
                    <span
                      className="font-mono text-xs font-bold px-2 py-0.5 rounded border"
                      style={{
                        color: themeConfig.primaryHex,
                        borderColor: themeConfig.primaryHex + '40',
                        background: themeConfig.primaryHex + '12',
                      }}
                    >
                      {settings.voiceRate.toFixed(2)}x
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0.75"
                    max="1.5"
                    step="0.05"
                    value={settings.voiceRate}
                    onChange={(e) =>
                      onUpdateSettings({ voiceRate: parseFloat(e.target.value) })
                    }
                    className="w-full h-1.5 bg-slate-800 rounded-lg cursor-pointer transition-all"
                    style={{ accentColor: themeConfig.primaryHex }}
                  />
                </div>
              </div>
            </div>

                  {/* TTS Voice Selector */}
                  <div className="p-4 space-y-3 border-t border-slate-800/80">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-300 font-medium">Stella Voice</span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {ttsVoices.find((v) => v.active)?.name || 'Bella (Leokani Dala)'}
                      </span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {ttsVoices.map((voice) => (
                        <button
                          key={voice.id}
                          type="button"
                          onClick={() => {
                            onChangeTtsVoice(voice.id);
                            onChangeTtsProvider(voice.provider);
                          }}
                          className={`flex items-center gap-2 p-3 rounded-xl border transition-all ${
                            voice.active
                              ? 'bg-cyan-950/40 border-cyan-400/80 text-white shadow-md'
                              : 'bg-[#10121a] border-slate-800 text-slate-400 hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            {voice.active && (
                              <span className="w-3 h-3 rounded-full bg-cyan-400 shrink-0" />
                            )}
                            <span className="text-xs font-medium text-white truncate">
                              {voice.name}
                            </span>
                          </div>
                          <span className="text-[10px] text-slate-500 block truncate">
                            {voice.description}
                          </span>
                        </button>
                      ))}
                    </div>
                    <p className="text-[10px] text-slate-500">
                      Leokani Dala (Kokoro-82M) runs locally on the backend. Edge is the online fallback.
                    </p>
                  </div>


            {/* ONBOARDING REPLAY & HELP */}
            <div className="space-y-2">
              <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase px-1">
                Guides & Walkthrough
              </span>

              <div className="rounded-2xl bg-[#14161d] border border-slate-800 p-4">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onReplayOnboarding();
                  }}
                  className="w-full flex items-center justify-between text-left hover:opacity-90 transition-opacity"
                >
                  <div className="flex items-center gap-3">
                    <HelpCircle className="w-5 h-5 shrink-0" style={{ color: themeConfig.primaryHex }} />
                    <div>
                      <h4 className="text-sm font-medium text-white">Replay Onboarding Guide</h4>
                      <p className="text-xs text-slate-400">
                        View feature overview for wake words, streaming speech, and device linking
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </button>
              </div>
            </div>

            {/* UTILITY */}
            <div className="space-y-2">
              <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase px-1">
                Utility
              </span>

              <div className="rounded-2xl bg-[#14161d] border border-slate-800 divide-y divide-slate-800/80 overflow-hidden">
                <div className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Globe className="w-5 h-5 text-slate-400" />
                    <span className="text-sm text-slate-200">App language</span>
                  </div>
                  <span className="text-xs text-slate-400 font-medium">English</span>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    onClearHistory();
                    showToast('Temporary conversation cache cleared.');
                  }}
                  className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-800/40 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Trash2 className="w-5 h-5 text-slate-400" />
                    <span className="text-sm text-slate-200">Clear temporary files</span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </button>
              </div>
            </div>

            {/* RESET BUTTON */}
            <div className="pt-2">
              <button
                type="button"
                onClick={() => {
                  if (confirm('Reset Stella settings to factory defaults?')) {
                    onUpdateSettings({
                      isDefaultAssistant: false,
                      startListeningOnOpen: true,
                      attachScreenshotOnInvoke: true,
                      wakeWordEnabled: true,
                      theme: 'void',
                      animateBackground: true,
                      autoSpeakResponse: true,
                    });
                    showToast('Stella has been reset to defaults.');
                  }
                }}
                className="w-full py-3.5 px-4 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-400 font-medium text-sm transition-colors text-center"
              >
                Reset Stella
              </button>
            </div>
          </div>

          {/* ABOUT STELLA */}
          <div className="space-y-2">
            <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase px-1">
              About Stella
            </span>
            <div className="rounded-2xl bg-[#14161d] border border-slate-800 p-4">
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 shrink-0" style={{ color: themeConfig.primaryHex }} />
                <div>
                  <h4 className="text-sm font-medium text-white">Stella</h4>
                  <p className="text-xs text-slate-400">
                    Your AI assistant that molds to your workflow, voice, and daily needs.
                  </p>
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Voice: Stella-TTS small model (7M params) &bull; Theme: {settings.theme} &bull; Backend: Stella agent + skills
              </p>
            </div>
          </div>

          {/* Toast Alert */}
          {toastMessage && (
            <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50 px-4 py-2 bg-slate-900 border border-slate-700 text-white text-xs rounded-full shadow-2xl">
              {toastMessage}
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
