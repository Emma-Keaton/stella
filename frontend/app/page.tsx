'use client';

import React, { useState, useEffect, useRef, useCallback, useSyncExternalStore } from 'react';

const emptySubscribe = () => () => {};
import { motion, AnimatePresence } from 'motion/react';
import { useStellaConnection } from '@/hooks/use-stella-connection';
import { setTtsVoice, getTtsVoice } from '@/lib/audio';
import { createWSMessage, stellaWS } from '@/lib/websocket';
import {
  Menu,
  Sparkles,
  SquarePen,
  Mic,
  MicOff,
  Sliders,
  Plus,
  Send,
  Maximize2,
  Volume2,
  VolumeX,
  Smartphone,
  Layers,
  Monitor,
  CheckCircle2,
  Clock,
  Battery,
  Flashlight,
  Wifi,
  Sun,
  RotateCcw,
  Bot,
  Activity,
  Radio,
  Share2,
  HardDrive,
  MapPin,
  Compass,
  Navigation,
} from 'lucide-react';
import {
  AssistantSettings,
  ChatMessage,
  DeviceState,
  Workspace,
  ProviderType,
  DeferredTask,
  LocalGgufModel,
  TTSVoice,
  TTSProviderType,
} from '@/lib/types';
import { sounds, speakText, stopSpeaking, SpeechStreamQueue, setMasterAudioVolume, STELLA_TTS_CONFIG } from '@/lib/audio';

// Stella backend WebSocket IPC (persistent connection via stellaWS, see lib/websocket.ts)

async function queryStellaBackend({
  prompt,
  history,
  deviceState,
  screenContext,
  onChunk,
  provider = 'gemini',
  localGgufModel = null,
}: {
  prompt: string;
  history: any[];
  deviceState: any;
  screenContext: string | undefined;
  onChunk: (text: string) => void;
  provider?: ProviderType;
  localGgufModel?: LocalGgufModel | null;
}): Promise<string> {
  const contextPromptParts: string[] = [];
  if (deviceState) {
    contextPromptParts.push(
      `[CURRENT DEVICE STATUS: Volume=${deviceState.volume}%, Brightness=${deviceState.brightness}%, Flashlight=${deviceState.flashlight ? 'ON' : 'OFF'}, Wi-Fi=${deviceState.wifi ? 'CONNECTED' : 'DISCONNECTED'}, Bluetooth=${deviceState.bluetooth ? 'ON' : 'OFF'}, DND=${deviceState.dnd ? 'ACTIVE' : 'OFF'}, Battery=${deviceState.batteryLevel}%]`
    );
  }
  if (screenContext) {
    contextPromptParts.push(`[ATTACHED ACTIVE SCREEN CONTEXT: "${screenContext}"]`);
  }
  const fullPrompt = [...contextPromptParts, `User: ${prompt || 'Analyze my current screen'}`].join('\n');

  const id = 'stella-' + Date.now() + '-' + Math.random().toString(36).slice(2, 9);

  const result = await stellaWS.request(
    createWSMessage('agent.run', {
      text: fullPrompt,
      provider,
      localGgufModel,
      context: { source: 'web', history, deviceState, screenContext },
    }),
    60000
  );

  const resultText: string = result?.result ?? result?.reply ?? '';

  // Simulate token streaming for typing + speech
  const words = resultText.split(/(\s+)/);
  let i = 0;
  return new Promise((resolve) => {
    const pump = () => {
      if (i >= words.length) {
        resolve(resultText);
        return;
      }
      onChunk(words[i]);
      i++;
      setTimeout(pump, 15);
    };
    pump();
  });
}
import { THEME_CONFIGS, applyTheme } from '@/lib/theme';
import { WorkspacesDrawer } from '@/components/WorkspacesDrawer';
import { SettingsModal } from '@/components/SettingsModal';
import { DeviceAssistantModal } from '@/components/DeviceAssistantModal';
import { DeviceControlPanel } from '@/components/DeviceControlPanel';
import { ScreenContextSimulator } from '@/components/ScreenContextSimulator';
import { AskWithStellaMenu } from '@/components/AskWithStellaMenu';
import { StellaOrb } from '@/components/StellaOrb';
import { StarSpinner } from '@/components/StarSpinner';
import { OnboardingModal } from '@/components/OnboardingModal';
import { DeviceLinkModal } from '@/components/DeviceLinkModal';
import { BatteryIndicator } from '@/components/BatteryIndicator';
import { LocationMapsModal } from '@/components/LocationMapsModal';


const INITIAL_PROMPT_SUGGESTIONS = [
  {
    icon: '💬',
    text: 'Hello Stella, what can you help me with?',
  },
  {
    icon: '🔦',
    text: 'Turn on flashlight and set device volume to 80%',
  },
  {
    icon: '⏱️',
    text: 'Set a 15-minute timer for my focus session',
  },
  {
    icon: '📝',
    text: 'Draft a concise update about our on-device AI assistant launch',
  },
];

export default function StellaApp() {
  // Device Hardware State
  const [deviceState, setDeviceState] = useState<DeviceState>({
    volume: 70,
    isMuted: false,
    brightness: 85,
    flashlight: false,
    wifi: true,
    bluetooth: true,
    dnd: false,
    batteryLevel: 92,
    isCharging: false,
    lowPowerMode: false,
    activeTimers: [],
    reminders: [
      { id: '1', title: 'Test Stella real-time voice streaming', completed: true },
    ],
    recentApps: ['Camera', 'Maps', 'Notes', 'Settings'],
  });

  // Backend WebSocket connection status (persistent connection with auto-reconnect)
  const { status: connStatus, isConnected: wsConnected, connect: wsConnect, request, onMessage, lastConnectedAt, lastDisconnectedAt } = useStellaConnection();

  // Hydration-safe theme retrieval from localStorage
  const savedTheme = useSyncExternalStore(
    emptySubscribe,
    () => {
      try {
        return (localStorage.getItem('stella_theme') as any) || 'void';
      } catch {
        return 'void';
      }
    },
    () => 'void'
  );

  // Assistant Configuration & Settings
  const [settings, setSettings] = useState<AssistantSettings>({
    isDefaultAssistant: true,
    startListeningOnOpen: true,
    attachScreenshotOnInvoke: true,
    wakeWordEnabled: true,
    wakeWordPhrase: 'hey stella',
    contextAwarenessEnabled: true,
    theme: savedTheme,
    animateBackground: true,
    voicePitch: 1.0,
    voiceRate: 1.05,
    autoSpeakResponse: true,
    autoRespondOnPause: true,
    pauseThresholdMs: 1400, // Detects silence after 1.4s of speaking and triggers response
    soundEffects: true,
    hapticFeedback: true,
    ttsProvider: 'auto',
    ttsVoiceId: 'af_bella',
  });

  // Initialize TTS voice from settings
  useEffect(() => {
    setTtsVoice(settings.ttsVoiceId || 'af_bella');
  }, [settings.ttsVoiceId]);

  // TTS Voice & Provider State
  const [ttsVoices, setTtsVoices] = useState<TTSVoice[]>([
    {
      id: 'af_bella',
      name: 'Bella',
      provider: 'kokoro',
      gender: 'female',
      language: 'en-US',
      description: 'Warm, friendly female voice (Kokoro)',
      active: true,
    },
    {
      id: 'am_adam',
      name: 'Adam',
      provider: 'kokoro',
      gender: 'male',
      language: 'en-US',
      description: 'Clear, confident male voice (Kokoro)',
      active: false,
    },
    {
      id: 'edge_en-us-aria',
      name: 'Aria',
      provider: 'edge',
      gender: 'female',
      language: 'en-US',
      description: 'Natural female voice (Edge TTS)',
      active: false,
    },
    {
      id: 'edge_en-us-guy',
      name: 'Guy',
      provider: 'edge',
      gender: 'male',
      language: 'en-US',
      description: 'Natural male voice (Edge TTS)',
      active: false,
    },
  ]);

  const handleChangeTtsVoice = useCallback((voiceId: string) => {
    setTtsVoices((prev) => prev.map((v) => ({ ...v, active: v.id === voiceId })));
    setSettings((prev) => ({ ...prev, ttsVoiceId: voiceId }));
  }, []);

  const handleChangeTtsProvider = useCallback((provider: TTSProviderType) => {
    setSettings((prev) => ({ ...prev, ttsProvider: provider }));
  }, []);

  // Sync theme to root CSS & localStorage on mount/update
  useEffect(() => {
    const currentTh = settings.theme || savedTheme || 'void';
    applyTheme(currentTh);
    try {
      localStorage.setItem('stella_theme', currentTh);
    } catch {}
  }, [settings.theme, savedTheme]);

  // Workspaces & Chat Threads – persisted in backend workspace_store
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string>('personal');
  const [activeThreadId, setActiveThreadId] = useState<string>('');

  // Messages in current thread – loaded from backend
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // Load workspaces & active thread from backend on mount / connection
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const wsRes = await request('workspace.list_workspaces', {});
        if (!cancelled && wsRes?.workspaces) {
          const wsList: Workspace[] = wsRes.workspaces.map((w:any)=>({
            id: w.id,
            name: w.name,
            threads: []
          }));
          setWorkspaces(wsList);
          if (!activeWorkspaceId && wsList[0]) setActiveWorkspaceId(wsList[0].id);
        }
        const convRes = await request('workspace.get_active_conversation', {});
        if (!cancelled && convRes?.conversation_id) {
          setActiveThreadId(convRes.conversation_id);
          const msgRes = await request('workspace.get_conversation', { id: convRes.conversation_id });
          if (msgRes?.messages) {
            setMessages(msgRes.messages.map((m:any)=>({
              id: `${convRes.conversation_id}-${m.timestamp}`,
              role: m.role,
              content: m.content,
            })));
          }
        }
      } catch {}
    }
    load();
    // Voice streaming listener
    const unsub = onMessage((msg:any)=>{
      if(msg.endpoint==='voice.stream' && msg.result?.audio){
        const audio = msg.result.audio;
        const blob = audio instanceof Blob ? audio : new Blob([audio], {type:'audio/wav'});
        const url = URL.createObjectURL(blob);
        const a = new Audio(url);
        a.play().catch(()=>{});
      }
    });
    return ()=>{ cancelled=true; unsub(); };
  }, []);

  // Modals & Drawers
  const [isWorkspacesOpen, setIsWorkspacesOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isDeviceAssistantOpen, setIsDeviceAssistantOpen] = useState(false);
  const [isDeviceControlsOpen, setIsDeviceControlsOpen] = useState(false);
  const [isScreenContextOpen, setIsScreenContextOpen] = useState(false);
  const [isDeviceLinkOpen, setIsDeviceLinkOpen] = useState(false);
  const [isMapsOpen, setIsMapsOpen] = useState(false);
  const [mapsInitialQuery, setMapsInitialQuery] = useState('');
  const [mapsInitialRoute, setMapsInitialRoute] = useState<{ origin: string; destination: string } | undefined>(undefined);
  const [mapsInitialMode, setMapsInitialMode] = useState<'search' | 'directions' | 'distance'>('search');
  const isMounted = useSyncExternalStore(emptySubscribe, () => true, () => false);
  const [showSplash, setShowSplash] = useState(true);
  const [dismissedOnboarding, setDismissedOnboarding] = useState(false);
  const isInitialOnboardingNeeded = useSyncExternalStore(
    emptySubscribe,
    () => {
      try {
        return localStorage.getItem('stella_onboarding_completed') !== 'true';
      } catch {
        return false;
      }
    },
    () => false
  );
  const showOnboarding = isInitialOnboardingNeeded && !dismissedOnboarding;

  // Active Provider & Model Preferences
  const [activeProvider, setActiveProvider] = useState<ProviderType>('gemini');
  const [activeModel, setActiveModel] = useState<string>('');
  const [localGgufModel, setLocalGgufModel] = useState<LocalGgufModel | null>(null);

  // Provider configuration lifecycle:
  //  - apiKeyTested: user's key has been verified against the provider
  //  - modelsPulled: authorized model list has been fetched
  //  - modelAuthorized: user selected a model that is authorized
  const [apiKeyTested, setApiKeyTested] = useState(false);
  const [modelsPulled, setModelsPulled] = useState(false);
  const [modelAuthorized, setModelAuthorized] = useState(false);

  // Derived "active" status: backend reachable + key tested + models pulled + model selected
  const isModelActive =
    wsConnected &&
    apiKeyTested &&
    modelsPulled &&
    modelAuthorized &&
    !!activeModel;

  // Callbacks exposed to SettingsModal so it can report configuration milestones
  const onProviderConfigured = useCallback(() => {
    setApiKeyTested(true);
    setModelsPulled(true);
    setModelAuthorized(true);
  }, []);

  const onModelDeauthorized = useCallback(() => {
    setApiKeyTested(false);
    setModelsPulled(false);
    setModelAuthorized(false);
  }, []);

  // Client hydration splash timer
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowSplash(false);
    }, 700);
    return () => clearTimeout(timer);
  }, []);

  // Active Screen Context
  const [activeScreenContext, setActiveScreenContext] = useState<{
    text: string;
    title: string;
  } | null>(null);

  // User input & Transcription state
  const [inputText, setInputText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPausing, setIsPausing] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [wakeWordDetected, setWakeWordDetected] = useState(false);

  // References
  const recognitionRef = useRef<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const speechAccumulatorRef = useRef<string>('');
  const speechStreamQueueRef = useRef<SpeechStreamQueue | null>(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking, liveTranscript]);

  // Synchronize Real-time Master Audio Volume with Device Hardware State & DND
  useEffect(() => {
    const effectiveVolume = deviceState.isMuted || deviceState.dnd ? 0 : deviceState.volume / 100;
    setMasterAudioVolume(effectiveVolume);
    if (deviceState.dnd) {
      stopSpeaking();
    }
  }, [deviceState.volume, deviceState.isMuted, deviceState.dnd]);

  // Execute detected device actions
  const applyDeviceAction = useCallback(
    (action: any) => {
      if (!action || !action.type) return;

      if (settings.soundEffects && !deviceState.dnd) {
        sounds.playActionChime();
      }

      switch (action.type) {
        case 'set_volume': {
          const vol = Math.min(
            100,
            Math.max(0, action.parameters?.volume ?? deviceState.volume)
          );
          const mute = action.parameters?.mute ?? (vol === 0);
          setDeviceState((prev) => ({
            ...prev,
            volume: vol,
            isMuted: mute,
            dnd: vol > 0 ? false : prev.dnd,
          }));
          break;
        }
        case 'set_brightness': {
          const br = Math.min(
            100,
            Math.max(10, action.parameters?.brightness ?? deviceState.brightness)
          );
          setDeviceState((prev) => ({ ...prev, brightness: br }));
          break;
        }
        case 'toggle_flashlight': {
          const on = action.parameters?.on ?? !deviceState.flashlight;
          setDeviceState((prev) => ({ ...prev, flashlight: on }));
          break;
        }
        case 'toggle_wifi': {
          const en = action.parameters?.enabled ?? !deviceState.wifi;
          setDeviceState((prev) => ({ ...prev, wifi: en }));
          break;
        }
        case 'toggle_bluetooth': {
          const en = action.parameters?.enabled ?? !deviceState.bluetooth;
          setDeviceState((prev) => ({ ...prev, bluetooth: en }));
          break;
        }
        case 'toggle_dnd': {
          const en = action.parameters?.enabled ?? !deviceState.dnd;
          if (en) {
            stopSpeaking();
            setDeviceState((prev) => ({
              ...prev,
              dnd: true,
              volume: 0,
              isMuted: true,
            }));
          } else {
            setDeviceState((prev) => ({
              ...prev,
              dnd: false,
              volume: 70,
              isMuted: false,
            }));
          }
          break;
        }
        case 'set_timer': {
          const secs = action.parameters?.seconds || 300;
          const label = action.parameters?.label || 'Timer';
          const newTimer = {
            id: Date.now().toString(),
            label,
            totalSeconds: secs,
            remainingSeconds: secs,
            isRunning: true,
          };
          setDeviceState((prev) => ({
            ...prev,
            activeTimers: [...prev.activeTimers, newTimer],
          }));
          break;
        }
        case 'add_reminder': {
          const title = action.parameters?.title || 'Reminder';
          const newRem = {
            id: Date.now().toString(),
            title,
            completed: false,
          };
          setDeviceState((prev) => ({
            ...prev,
            reminders: [...prev.reminders, newRem],
          }));
          break;
        }
        case 'show_map':
        case 'search_nearby': {
          const q = action.parameters?.query || '';
          setMapsInitialQuery(q);
          setMapsInitialMode('search');
          setIsMapsOpen(true);
          break;
        }
        case 'get_directions': {
          const orig = action.parameters?.origin || 'My Location';
          const dest = action.parameters?.destination || '';
          setMapsInitialRoute({ origin: orig, destination: dest });
          setMapsInitialMode('directions');
          setIsMapsOpen(true);
          break;
        }
        case 'measure_distance': {
          setMapsInitialMode('distance');
          setIsMapsOpen(true);
          break;
        }
        default:
          break;
      }
    },
    [
      settings.soundEffects,
      deviceState.volume,
      deviceState.brightness,
      deviceState.flashlight,
      deviceState.wifi,
      deviceState.bluetooth,
      deviceState.dnd,
    ]
  );

  // Stop voice listening
  const stopListening = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
    }
    setIsListening(false);
    setIsPausing(false);
  }, []);

  // Send message and stream tokens BOTH in speech and typing
  const handleSendMessage = useCallback(
    async (textToSend?: string) => {
      const prompt = (textToSend || inputText || liveTranscript).trim();
      if (!prompt && !activeScreenContext) return;

      // Reset live inputs
      setInputText('');
      setLiveTranscript('');
      speechAccumulatorRef.current = '';
      stopListening();

      // Stop any prior speech
      if (speechStreamQueueRef.current) {
        speechStreamQueueRef.current.cancel();
      }

      // Add User Message to the main chat screen
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'user',
        content: prompt,
        timestamp: new Date().toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        }),
        screenAttachment: activeScreenContext?.title,
      };

      // Create an empty Assistant Message placeholder for streaming
      const assistantMessageId = (Date.now() + 1).toString();
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        spokenText: '',
        timestamp: new Date().toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        }),
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsThinking(true);

      // Initialize Streaming Speech Queue
      if (settings.autoSpeakResponse) {
        speechStreamQueueRef.current = new SpeechStreamQueue({
          rate: settings.voiceRate,
          pitch: settings.voicePitch,
          onStart: () => setIsSpeaking(true),
          onEnd: () => setIsSpeaking(false),
        });
      }

      try {
        let accumulatedFullText = '';
        let detectedAction: any = null;

        await queryStellaBackend({
          prompt,
          history: messages,
          deviceState,
          screenContext: activeScreenContext?.text,
          onChunk: (text) => {
            accumulatedFullText += text;

            // Stream tokens in typing (UI)
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId
                  ? {
                      ...m,
                      content: accumulatedFullText.replace(
                        /\[ACTION:[\s\S]*?\]/g,
                        ''
                      ),
                    }
                  : m
              )
            );

            // Stream tokens in speech concurrently!
            if (settings.autoSpeakResponse && speechStreamQueueRef.current) {
              speechStreamQueueRef.current.pushChunk(text);
            }
          },
        });

        // Finish speech stream queue
        if (settings.autoSpeakResponse && speechStreamQueueRef.current) {
          speechStreamQueueRef.current.finish();
        }

        // Check for device action tag at end: [ACTION:{...}]
        const actionMatch = /\[ACTION:([\s\S]*?)\]/.exec(accumulatedFullText);
        if (actionMatch) {
          try {
            detectedAction = JSON.parse(actionMatch[1]);
            applyDeviceAction(detectedAction);
          } catch {}
        }

        // Finalize message clean text
        const cleanContent = accumulatedFullText
          .replace(/\[ACTION:[\s\S]*?\]/g, '')
          .trim();

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessageId
              ? {
                  ...m,
                  content: cleanContent || 'Task completed.',
                  spokenText: cleanContent,
                  deviceAction: detectedAction
                    ? {
                        type: detectedAction.type,
                        description:
                          detectedAction.feedback || 'Hardware action executed',
                        status: 'success',
                        data: detectedAction.parameters,
                      }
                    : undefined,
                }
              : m
          )
        );
      } catch (err) {
        console.error(err);
        sounds.playErrorChime();
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessageId
              ? {
                  ...m,
                  content:
                    'I experienced a brief transmission pause. Please speak or type again.',
                }
              : m
          )
        );
      } finally {
        setIsThinking(false);
      }
    },
    [
      inputText,
      liveTranscript,
      activeScreenContext,
      stopListening,
      messages,
      deviceState,
      settings.autoSpeakResponse,
      settings.voiceRate,
      settings.voicePitch,
      applyDeviceAction,
    ]
  );

  const handleSendMessageRef = useRef(handleSendMessage);
  useEffect(() => {
    handleSendMessageRef.current = handleSendMessage;
  }, [handleSendMessage]);

  // Speech Recognition & Silence / Pause Detection
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const SpeechRec =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRec) return;

    const recognition = new SpeechRec();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event: any) => {
      let interim = '';
      let final = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          final += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }

      const currentSpeech = (final || interim).trim();
      setLiveTranscript(currentSpeech);
      speechAccumulatorRef.current = currentSpeech;

      // Check Wake Word: "hey stella", "ok stella", "stella"
      const lower = currentSpeech.toLowerCase();
      const wakePhrases = [
        'hey stella',
        'ok stella',
        'okay stella',
        'hi stella',
        'stella',
      ];
      const matchedPhrase = wakePhrases.find((p) => lower.includes(p));

      if (matchedPhrase && settings.wakeWordEnabled && !isThinking) {
        setWakeWordDetected(true);
        sounds.playWakeChime();

        // Extract trailing command directly on main chat screen
        const parts = lower.split(matchedPhrase);
        const trailingCommand = parts[parts.length - 1]?.trim();

        if (trailingCommand && trailingCommand.length > 2) {
          stopListening();
          handleSendMessageRef.current(trailingCommand);
          speechAccumulatorRef.current = '';
        }

        setTimeout(() => setWakeWordDetected(false), 2000);
        return;
      }

      // PAUSE DETECTION: When the user pauses for a moment, respond automatically!
      if (
        settings.autoRespondOnPause &&
        currentSpeech.length >= 2 &&
        !isThinking
      ) {
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
        }

        silenceTimerRef.current = setTimeout(() => {
          const textToSubmit = speechAccumulatorRef.current.trim();
          if (textToSubmit && textToSubmit.length >= 2 && !isThinking) {
            setIsPausing(true);
            if (settings.soundEffects) {
              sounds.playConfirmChime();
            }

            // Settle pause effect and submit directly to chat stream
            setTimeout(() => {
              stopListening();
              setIsPausing(false);
              handleSendMessageRef.current(textToSubmit);
              speechAccumulatorRef.current = '';
            }, 250);
          }
        }, settings.pauseThresholdMs || 1400);
      }
    };

    recognition.onspeechend = () => {
      // Automatic response when speech ceases
      if (
        settings.autoRespondOnPause &&
        speechAccumulatorRef.current.trim().length >= 2 &&
        !isThinking
      ) {
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
        setIsPausing(true);
        setTimeout(() => {
          const textToSubmit = speechAccumulatorRef.current.trim();
          stopListening();
          setIsPausing(false);
          if (textToSubmit) {
            handleSendMessageRef.current(textToSubmit);
            speechAccumulatorRef.current = '';
          }
        }, 300);
      }
    };

    recognition.onerror = (event: any) => {
      if (event.error !== 'no-speech') {
        console.warn('Speech event error:', event.error);
      }
      setIsListening(false);
      setIsPausing(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      setIsPausing(false);
    };

    recognitionRef.current = recognition;

    return () => {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      try {
        recognition.stop();
      } catch {}
    };
  }, [
    settings.wakeWordEnabled,
    settings.autoRespondOnPause,
    settings.pauseThresholdMs,
    settings.soundEffects,
    isThinking,
    stopListening,
  ]);

  // Start voice listening directly on the main chat screen
  const startListening = () => {
    if (!recognitionRef.current) {
      alert('Speech Recognition is not supported by your browser.');
      return;
    }

    try {
      stopSpeaking();
      if (speechStreamQueueRef.current) {
        speechStreamQueueRef.current.cancel();
      }
      setLiveTranscript('');
      speechAccumulatorRef.current = '';
      recognitionRef.current.start();
      setIsListening(true);
      if (settings.soundEffects) {
        sounds.playWakeChime();
      }
    } catch {
      setIsListening(true);
    }
  };

  // Replay speech for a message
  const handleReplaySpeech = (text: string) => {
    if (isSpeaking) {
      stopSpeaking();
      setIsSpeaking(false);
      return;
    }
    speakText(text, {
      rate: settings.voiceRate,
      pitch: settings.voicePitch,
      onStart: () => setIsSpeaking(true),
      onEnd: () => setIsSpeaking(false),
      onError: () => setIsSpeaking(false),
    });
  };

  // New Thread
  const handleNewThread = async () => {
    stopSpeaking();
    if (speechStreamQueueRef.current) speechStreamQueueRef.current.cancel();

    const res = await request('workspace.create_conversation',{workspace_id:activeWorkspaceId,title:'New Conversation'});
    if (res?.id) {
      setActiveThreadId(res.id);
      setMessages([]);
      setActiveScreenContext(null);
    }
  };

  // New Workspace
  const handleNewWorkspace = async () => {
    const name = prompt('Workspace Name:', 'Personal Workspace');
    if (!name) return;

    const res = await request('workspace.create_workspace',{name});
    if (res?.id) {
      setWorkspaces(prev=>[...prev,{id:res.id,name,threads:[] }]);
      setActiveWorkspaceId(res.id);
    }
  };

  const themeConfig = THEME_CONFIGS[settings.theme] || THEME_CONFIGS.void;

  const connPillDotClass =
    connStatus === 'connected'
      ? 'w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping'
      : connStatus === 'reconnecting'
        ? 'w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse'
        : 'w-1.5 h-1.5 rounded-full bg-rose-500';
  const connPillLabel =
    connStatus === 'connected' ? 'Backend Connected' : connStatus === 'reconnecting' ? 'Reconnecting...' : 'Disconnected';

  // Handle task deferred from Device Link Hub
  const handleTaskDeferred = (task: DeferredTask) => {
    const deferMessage: ChatMessage = {
      id: `defer-${Date.now()}`,
      role: 'assistant',
      content: `🚀 **Distributed Task Deferral Executed**\n• **Task**: ${task.title}\n• **Target Node**: ${task.targetDevice}\n• **Status**: Completed\n• **Telemetry**: ${task.result || 'Execution verified on linked hardware.'}`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, deferMessage]);
    if (settings.soundEffects) {
      sounds.playConfirmChime();
    }
  };

  return (
    <div
      className="relative h-screen h-[100dvh] w-full max-w-full bg-[#030509] text-slate-100 flex flex-col font-sans overflow-hidden transition-colors duration-500"
      style={{
        // Global theme CSS variables
        ['--theme-primary' as any]: themeConfig.primaryHex,
        ['--theme-secondary' as any]: themeConfig.secondaryHex,
      }}
    >
      {/* 4-POINTER GEMINI STAR INITIAL SPLASH LOADER */}
      <AnimatePresence>
        {showSplash && (
          <motion.div
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="fixed inset-0 z-50 pointer-events-none"
          >
            <StarSpinner
              isSplash={true}
              theme={settings.theme}
              text="Initializing Stella..."
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Device Torch illumination simulation when flashlight is on */}
      {deviceState.flashlight && (
        <div className="fixed inset-0 z-30 bg-white/95 pointer-events-none mix-blend-screen animate-pulse" />
      )}

      {/* Futuristic Ambient Atmosphere Glow - Reactive to Theme */}
      <div
        className="fixed top-0 left-1/2 -translate-x-1/2 w-full max-w-[100vw] h-[450px] rounded-full blur-[140px] pointer-events-none opacity-30 transition-all duration-700 overflow-hidden"
        style={{ background: themeConfig.bgGlowGradient }}
      />

      {/* TOP BAR: Clean Header with Reactive Neon Theme Accents */}
      <header
        className="shrink-0 sticky top-0 z-30 w-full max-w-full overflow-hidden bg-[#030509]/90 backdrop-blur-2xl border-b px-3 sm:px-6 py-2.5 sm:py-3 flex items-center justify-between gap-2 shadow-[0_4px_25px_rgba(0,0,0,0.5)] transition-colors duration-500"
        style={{ borderColor: themeConfig.primaryHex + '25' }}
      >
        {/* Zone 1: Menu & Brand */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={() => setIsWorkspacesOpen(true)}
            className="w-9 h-9 rounded-xl flex items-center justify-center text-slate-300 hover:text-white hover:bg-[#0c1222] border border-transparent transition-all"
            style={{
              borderColor: 'rgba(255,255,255,0.06)',
            }}
            title="Workspaces"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2">
            <span
              className="w-2.5 h-2.5 rounded-full animate-pulse transition-colors"
              style={{
                backgroundColor: themeConfig.primaryHex,
                boxShadow: `0 0 12px ${themeConfig.primaryHex}`,
              }}
            />
            <span
              className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5 transition-all"
              style={{ textShadow: `0 0 12px ${themeConfig.primaryHex}50` }}
            >
              Stella
            </span>
          </div>
        </div>

        {/* Zone 2: Model & Status Pill */}
        <div className="hidden sm:flex items-center justify-center gap-2">
          <button
            type="button"
            onClick={() => setIsSettingsOpen(true)}
            className="flex items-center gap-2 px-3.5 py-1 rounded-full border text-xs transition-all group"
            style={{
              borderColor: isModelActive
                ? themeConfig.primaryHex + '50'
                : themeConfig.primaryHex + '25',
              background: isModelActive
                ? `${themeConfig.primaryHex}15`
                : '#090d18',
              boxShadow: isModelActive
                ? `0 0 12px ${themeConfig.primaryHex}25`
                : `0 0 12px ${themeConfig.primaryHex}10`,
            }}
            title="Change Model & Provider"
          >
            <Sparkles
              className="w-3.5 h-3.5 group-hover:rotate-12 transition-transform"
              style={{ color: isModelActive ? themeConfig.primaryHex : '#94a3b8' }}
            />
            <span className="font-medium text-slate-100 truncate max-w-[160px]">
              {(() => {
                const providerDisplayName = activeProvider
                  .split('_')
                  .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                  .join(' ');

                // Local GGUF models are active when loaded (no API key needed)
                if (localGgufModel) {
                  return `[Local GGUF] ${localGgufModel.fileName}`;
                }
                // Fully active: key tested + models pulled + model authorized + backend connected
                if (isModelActive) {
                  return `${activeModel} • ${providerDisplayName}`;
                }
                // Provider selected but key not tested → provider name only, inactive
                if (activeProvider && !apiKeyTested) {
                  return providerDisplayName;
                }
                // Key tested but backend/network offline → show model+provider but inactive
                if (activeModel && apiKeyTested && !wsConnected) {
                  return `${activeModel} • ${providerDisplayName}`;
                }
                return 'No Model Active';
              })()}
            </span>
            {isModelActive || (localGgufModel && wsConnected) ? (
              <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                active
              </span>
            ) : (
              <span className="text-[10px] text-slate-500 font-mono flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-700" />
                inactive
              </span>
            )}
          </button>
{/* Backend Connection Status Pill */}
          <button
            type="button"
            onClick={wsConnect}
            className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-all hover:opacity-90"
            style={{
    background: connStatus === 'connected' ? '#064e3b15' : connStatus === 'reconnecting' ? '#713f1215' : '#451a0315',
    borderColor: connStatus === 'connected' ? '#4ade8050' : connStatus === 'reconnecting' ? '#fbbf2450' : '#78350f50',
    color: connStatus === 'connected' ? '#4ade80' : connStatus === 'reconnecting' ? '#fbbf24' : '#f97316'
}}
            title={"Backend WebSocket: " + connStatus}
            suppressHydrationWarning
          >
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
            <span suppressHydrationWarning>
              {connStatus === 'connected' ? 'Backend Connected' : connStatus === 'reconnecting' ? 'Reconnecting...' : 'Disconnected'}
            </span>
          </button>

          {/* Device Link Hub Pill */}
          <button
            type="button"
            onClick={() => setIsDeviceLinkOpen(true)}
            className="hidden lg:flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-all hover:opacity-90"
            style={{
              background: themeConfig.primaryHex + '15',
              borderColor: themeConfig.primaryHex + '40',
              color: themeConfig.primaryHex,
            }}
            title="Open Device Link Hub (Cross-Connect Up to 5 Devices)"
          >
            <span>🔗</span>
            <span>Device Link</span>
          </button>
        </div>

        {/* Zone 3: Hardware HUD, Battery Indicator, New Thread & Voice Mode Status */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Real-Time Visual Battery Indicator */}
          <BatteryIndicator
            deviceState={deviceState}
            theme={settings.theme}
            onClick={() => setIsDeviceControlsOpen(true)}
          />

          {/* Wake Word Status Tag */}
          {settings.wakeWordEnabled && (
            <button
              type="button"
              onClick={() => {
                setWakeWordDetected(true);
                sounds.playWakeChime();
                startListening();
                setTimeout(() => setWakeWordDetected(false), 2000);
              }}
              title="Wake word active: Say 'Hey Stella' or click to test"
              className={`hidden md:flex items-center gap-1.5 px-3 py-1 rounded-full text-xs transition-all ${
                wakeWordDetected
                  ? 'text-slate-950 font-bold animate-bounce'
                  : 'hover:opacity-90'
              }`}
              style={{
                backgroundColor: wakeWordDetected ? themeConfig.primaryHex : themeConfig.primaryHex + '15',
                borderColor: themeConfig.primaryHex + '40',
                color: wakeWordDetected ? '#000000' : themeConfig.primaryHex,
                borderWidth: '1px',
                boxShadow: wakeWordDetected ? `0 0 20px ${themeConfig.primaryHex}` : undefined,
              }}
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Say &ldquo;Hey Stella&rdquo;</span>
            </button>
          )}

          {/* Quick Hardware Controls Toggle */}
          <button
            type="button"
            onClick={() => setIsDeviceControlsOpen(true)}
            className={`w-9 h-9 rounded-xl flex items-center justify-center text-slate-300 hover:text-white hover:bg-[#0e1424] border transition-all ${
              deviceState.flashlight
                ? 'border-amber-400 bg-amber-400/20 text-amber-300 shadow-[0_0_15px_rgba(251,191,36,0.3)]'
                : 'border-slate-800'
            }`}
            title="Device Controls"
          >
            <Sliders className="w-4 h-4" />
          </button>

          {/* Google Maps & Location Navigation Toggle */}
          <button
            type="button"
            onClick={() => {
              setMapsInitialMode('search');
              setIsMapsOpen(true);
            }}
            className="w-9 h-9 rounded-xl flex items-center justify-center text-slate-300 hover:text-white hover:bg-[#0e1424] border border-slate-800 transition-all hover:border-emerald-500/50"
            title="Google Maps Location & Navigation"
          >
            <Compass className="w-4 h-4 text-emerald-400" />
          </button>

          {/* Device Link Quick Icon (for mobile) */}
          <button
            type="button"
            onClick={() => setIsDeviceLinkOpen(true)}
            className="w-9 h-9 rounded-xl flex items-center justify-center text-slate-300 hover:text-white hover:bg-[#0e1424] border border-slate-800 transition-all lg:hidden"
            title="Device Link Hub"
          >
            <Share2 className="w-4 h-4" />
          </button>

          {/* New Chat Button */}
          <button
            type="button"
            onClick={handleNewThread}
            className="w-9 h-9 rounded-xl flex items-center justify-center text-slate-300 hover:text-white hover:bg-[#0e1424] border border-slate-800 transition-all"
            title="New Chat"
          >
            <SquarePen className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* MAIN CHAT SCREEN: To and Fro recorded in real-time */}
      <main className="flex-1 min-h-0 max-w-4xl w-full mx-auto flex flex-col overflow-hidden px-3 sm:px-6 py-2">
        {messages.length === 0 && !isListening ? (
          /* Empty / Welcome Hero State matching screenshots */
          <div className="flex-1 min-h-0 overflow-y-auto flex flex-col items-center justify-start sm:justify-center text-center pt-8 sm:pt-12 pb-6 space-y-6 max-w-full overflow-x-hidden">
            {/* Interactive Glowing Stella Four-Pointed Star */}
            <div className="relative group cursor-pointer" onClick={startListening}>
              <StellaOrb
                isListening={isListening}
                isSpeaking={isSpeaking}
                isThinking={isThinking}
                theme={settings.theme}
                animateBackground={settings.animateBackground}
                size="md"
              />
              <div
                className="mt-4 flex items-center justify-center gap-2 text-xs font-medium transition-all group-hover:scale-105"
                style={{ color: themeConfig.primaryHex }}
              >
                <Mic className="w-3.5 h-3.5 animate-pulse" />
                <span>Tap star or say &ldquo;Hey Stella&rdquo; to start speaking</span>
              </div>
            </div>

            {/* Headline matching screenshot 1 */}
            <div className="space-y-2 max-w-md">
              <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white drop-shadow-[0_0_15px_rgba(255,255,255,0.15)]">
                What&apos;s on your mind?
              </h1>
              <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
                You can chat with Stella by voice or by text.
              </p>
            </div>

            {/* Suggestion Cards matching screenshot 1 & 7 */}
            <div className="w-full max-w-lg space-y-2.5 text-left">
              {INITIAL_PROMPT_SUGGESTIONS.map((sug, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleSendMessage(sug.text)}
                  className="w-full p-4 rounded-2xl bg-[#070b16]/80 hover:bg-[#0c1324] border text-left transition-all flex items-start gap-3.5 group hover:shadow-lg"
                  style={{
                    borderColor: themeConfig.primaryHex + '25',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = themeConfig.primaryHex + '70';
                    e.currentTarget.style.boxShadow = `0 0 20px ${themeConfig.primaryHex}20`;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = themeConfig.primaryHex + '25';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <span className="text-lg shrink-0 mt-0.5">{sug.icon}</span>
                  <div className="flex-1">
                    <p className="text-sm text-slate-200 group-hover:text-white transition-colors leading-snug">
                      {sug.text}
                    </p>
                  </div>
                </button>
              ))}
            </div>

            {/* Active Screen Context Preview if attached */}
            {activeScreenContext && (
              <div
                className="w-full max-w-lg p-3 rounded-2xl border flex items-center justify-between text-xs shadow-lg"
                style={{
                  background: themeConfig.primaryHex + '15',
                  borderColor: themeConfig.primaryHex + '40',
                  color: themeConfig.primaryHex,
                }}
              >
                <div className="flex items-center gap-2 truncate">
                  <Monitor className="w-4 h-4 shrink-0" />
                  <span className="font-medium truncate">
                    Attached Screen: {activeScreenContext.title}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveScreenContext(null)}
                  className="text-slate-400 hover:text-white"
                >
                  Remove
                </button>
              </div>
            )}
          </div>
        ) : (
          /* Live Chat Stream */
          <div ref={chatContainerRef} className="flex-1 min-h-0 w-full max-w-full space-y-4 py-3 overflow-y-auto overflow-x-hidden pr-1">
            {messages.map((msg, index) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex gap-2.5 sm:gap-3.5 max-w-full min-w-0 ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {/* Stella Avatar */}
                {msg.role === 'assistant' && (
                  <div
                    className="w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-slate-950 font-bold shrink-0 mt-1 shadow-md"
                    style={{
                      background: `linear-gradient(135deg, ${themeConfig.gradientStops.join(', ')})`,
                      boxShadow: `0 0 14px ${themeConfig.primaryHex}50`,
                    }}
                  >
                    <Sparkles className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-slate-950" />
                  </div>
                )}

                <div
                  className={`min-w-0 max-w-[85%] sm:max-w-xl rounded-2xl p-3 sm:p-4 space-y-2.5 transition-all overflow-hidden break-words [overflow-wrap:anywhere] ${
                    msg.role === 'user'
                      ? 'bg-[#0b1220] text-white rounded-br-sm'
                      : 'bg-[#080d19] text-slate-100 rounded-bl-sm'
                  }`}
                  style={{
                    borderColor:
                      msg.role === 'user'
                        ? themeConfig.primaryHex + '55'
                        : themeConfig.secondaryHex + '45',
                    borderWidth: '1px',
                    boxShadow:
                      msg.role === 'user'
                        ? `0 0 20px ${themeConfig.primaryHex}15`
                        : `0 0 25px ${themeConfig.secondaryHex}15`,
                  }}
                >
                  {/* Role Header */}
                  <div className="flex items-center justify-between text-[11px] pb-1 border-b border-slate-800/60">
                    <span
                      className="font-semibold uppercase tracking-wider"
                      style={{
                        color: msg.role === 'user' ? themeConfig.primaryHex : themeConfig.secondaryHex,
                      }}
                    >
                      {msg.role === 'user' ? 'You' : 'Stella'}
                    </span>
                    <span className="text-slate-500 font-mono">{msg.timestamp}</span>
                  </div>

                  {/* Attached Screen Context Badge */}
                  {msg.screenAttachment && (
                    <div
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium border max-w-full truncate"
                      style={{
                        background: themeConfig.primaryHex + '15',
                        borderColor: themeConfig.primaryHex + '40',
                        color: themeConfig.primaryHex,
                      }}
                    >
                      <Monitor className="w-3 h-3 shrink-0" />
                      <span className="truncate">{msg.screenAttachment}</span>
                    </div>
                  )}

                  {/* Streamed Token Message Content */}
                  <div className="text-sm leading-relaxed whitespace-pre-wrap font-sans break-words [overflow-wrap:anywhere]">
                    {msg.content}
                    {/* Live streaming token caret if currently thinking/streaming on last assistant message */}
                    {isThinking && index === messages.length - 1 && (
                      <span
                        className="inline-block w-2 h-4 ml-1 animate-pulse rounded-sm align-middle"
                        style={{
                          backgroundColor: themeConfig.primaryHex,
                          boxShadow: `0 0 8px ${themeConfig.primaryHex}`,
                        }}
                      />
                    )}
                  </div>

                  {/* Executed Hardware Action Result */}
                  {msg.deviceAction && (
                    <div className="mt-2 p-2.5 rounded-xl bg-emerald-500/15 border border-emerald-400/40 flex items-center justify-between text-xs text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.2)]">
                      <div className="flex items-center gap-2 truncate">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                        <span className="font-semibold truncate">
                          {msg.deviceAction.description}
                        </span>
                      </div>
                      <span className="text-[10px] text-emerald-400 uppercase tracking-widest font-mono shrink-0 ml-2">
                        Hardware Control
                      </span>
                    </div>
                  )}

                  {/* Voice Controls on Assistant Message */}
                  {msg.role === 'assistant' && msg.content && (
                    <div className="flex flex-wrap items-center justify-between gap-1.5 pt-1">
                      <button
                        type="button"
                        onClick={() =>
                          handleReplaySpeech(msg.spokenText || msg.content)
                        }
                        className="inline-flex items-center gap-1.5 text-xs hover:text-white transition-colors"
                        style={{ color: themeConfig.primaryHex }}
                        title="Replay Voice"
                      >
                        <Volume2 className="w-3.5 h-3.5 shrink-0" />
                        <span>Replay Voice</span>
                      </button>
                      {isSpeaking && index === messages.length - 1 && (
                        <div
                          className="flex items-center gap-1.5 text-[11px] font-medium animate-pulse"
                          style={{ color: themeConfig.secondaryHex }}
                        >
                          <Radio className="w-3 h-3 animate-spin shrink-0" />
                          <span>Speaking via Stella...</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </motion.div>
            ))}

            {/* LIVE RECORDING USER BUBBLE: Displays user's voice in real-time as they talk! */}
            {isListening && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-end gap-2.5 sm:gap-3.5 max-w-full min-w-0"
              >
                <div
                  className="min-w-0 max-w-[85%] sm:max-w-xl rounded-2xl p-3 sm:p-4 bg-[#091122] text-white rounded-br-sm space-y-2 border-2 break-words [overflow-wrap:anywhere] overflow-hidden"
                  style={{
                    borderColor: themeConfig.primaryHex,
                    boxShadow: `0 0 25px ${themeConfig.primaryHex}40`,
                  }}
                >
                  <div
                    className="flex items-center justify-between text-[11px] pb-1 border-b"
                    style={{ borderColor: themeConfig.primaryHex + '40' }}
                  >
                    <span
                      className="font-semibold uppercase tracking-wider flex items-center gap-1.5"
                      style={{ color: themeConfig.primaryHex }}
                    >
                      <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
                      Recording Voice...
                    </span>
                    {isPausing ? (
                      <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-400 text-[10px] animate-pulse">
                        Pause detected • Responding...
                      </span>
                    ) : (
                      <span className="text-slate-400 text-[10px]">
                        Pause speaking to send
                      </span>
                    )}
                  </div>

                  <p className="text-sm font-medium italic text-slate-100">
                    {liveTranscript || 'Listening... speak your request'}
                  </p>

                  {/* Soundwave animation */}
                  <div className="flex items-center gap-1 pt-1">
                    {[0, 1, 2, 3, 4, 5, 6].map((i) => (
                      <span
                        key={i}
                        className="w-1 rounded-full animate-soundwave"
                        style={{
                          backgroundColor: themeConfig.primaryHex,
                          boxShadow: `0 0 6px ${themeConfig.primaryHex}`,
                          animationDelay: `${i * 0.12}s`,
                          height: `${8 + (i % 3) * 6}px`,
                        }}
                      />
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      {/* FLOATING PROMPT INPUT BAR with Reactive Theme Accents */}
      <footer className="shrink-0 z-30 w-full max-w-4xl mx-auto px-4 sm:px-6 py-3 bg-[#030509]/95 border-t border-slate-800/50 backdrop-blur-xl">
        <div className="max-w-2xl mx-auto space-y-2">
          {/* Pause Status Indicator Banner if listening */}
          <AnimatePresence>
            {isListening && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                className="px-4 py-2 rounded-2xl bg-[#09101f]/90 border backdrop-blur-md flex items-center justify-between text-xs text-slate-200 shadow-xl"
                style={{
                  borderColor: themeConfig.primaryHex + '50',
                  boxShadow: `0 0 20px ${themeConfig.primaryHex}20`,
                }}
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping shrink-0" />
                  <span className="font-semibold text-white uppercase text-[10px] tracking-wider">
                    Voice Active:
                  </span>
                  <span className="italic truncate" style={{ color: themeConfig.primaryHex }}>
                    {liveTranscript || 'Listening to your speech...'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={stopListening}
                  className="px-3 py-1 rounded-lg bg-rose-500/80 hover:bg-rose-500 text-white font-medium text-xs transition-colors shrink-0 shadow-[0_0_10px_rgba(244,63,94,0.4)]"
                >
                  Done
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Floating Neon Input Bar */}
          <div
            className="relative rounded-3xl bg-[#060a16]/95 border-2 p-2 backdrop-blur-2xl flex items-center gap-2 transition-all duration-300"
            style={{
              borderColor: themeConfig.primaryHex + '40',
              boxShadow: `0 0 30px ${themeConfig.primaryHex}20`,
            }}
          >
            {/* Screen Context Attachment */}
            <button
              type="button"
              onClick={() => setIsScreenContextOpen(true)}
              className="w-10 h-10 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-[#0d1527] transition-all shrink-0"
              title="Attach Screen Context"
            >
              <Plus className="w-5 h-5" />
            </button>

            {/* Quick Hardware Controls */}
            <button
              type="button"
              onClick={() => setIsDeviceControlsOpen(true)}
              className="w-10 h-10 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-[#0d1527] transition-all shrink-0 hidden sm:flex"
              title="Device Hardware Controls"
            >
              <Sliders className="w-4 h-4" />
            </button>

            {/* Prompt Input */}
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder={
                isListening
                  ? 'Listening... pause speaking to submit'
                  : 'Enter your prompt or tap mic to speak'
              }
              className="flex-1 bg-transparent px-2 py-2 text-sm text-white placeholder-slate-500 focus:outline-none"
            />

            {/* Send Button OR Neon Mic Button */}
            {inputText.trim() ? (
              <button
                type="button"
                onClick={() => handleSendMessage()}
                className={`w-11 h-11 rounded-full text-slate-950 font-bold flex items-center justify-center transition-all shrink-0 active:scale-95 ${themeConfig.buttonGradient} ${themeConfig.buttonShadow}`}
                title="Send message"
              >
                <Send className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  if (isListening) stopListening();
                  else startListening();
                }}
                className={`w-11 h-11 rounded-full flex items-center justify-center transition-all shrink-0 active:scale-95 ${
                  isListening
                    ? 'bg-[#ff007f] text-white shadow-[0_0_25px_rgba(255,0,127,0.6)] border border-[#ff007f] animate-pulse'
                    : 'bg-[#0b1222] border hover:bg-[#101b33]'
                }`}
                style={{
                  borderColor: isListening ? '#ff007f' : themeConfig.primaryHex + '50',
                  color: isListening ? '#ffffff' : themeConfig.primaryHex,
                  boxShadow: isListening ? undefined : `0 0 15px ${themeConfig.primaryHex}25`,
                }}
                title={isListening ? 'Stop listening' : 'Start voice mode'}
              >
                {isListening ? (
                  <MicOff className="w-5 h-5" />
                ) : (
                  <Mic className="w-5 h-5" />
                )}
              </button>
            )}
          </div>
        </div>
      </footer>

      {/* WORKSPACES DRAWER */}
      <WorkspacesDrawer
        isOpen={isWorkspacesOpen}
        onClose={() => setIsWorkspacesOpen(false)}
        workspaces={workspaces}
        activeWorkspaceId={activeWorkspaceId}
        activeThreadId={activeThreadId}
        onSelectWorkspace={(id) => setActiveWorkspaceId(id)}
        onSelectThread={(tId) => {
          setActiveThreadId(tId);
        }}
        onNewThread={handleNewThread}
        onNewWorkspace={handleNewWorkspace}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onDeleteThread={async (threadId) => {
      
          await request('workspace.delete_conversation',{id:threadId});
          setActiveThreadId('');
          setMessages([]);
          // refresh threads
        }}
      />

      {/* SETTINGS MODAL */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        settings={settings}
        onUpdateSettings={(newSettings) =>
          setSettings((prev) => ({ ...prev, ...newSettings }))
        }
        onOpenDeviceAssistant={() => setIsDeviceAssistantOpen(true)}
        onOpenDeviceLink={() => setIsDeviceLinkOpen(true)}
        onReplayOnboarding={() => setDismissedOnboarding(false)}
        onClearHistory={() => setMessages([])}
        activeProvider={activeProvider}
        onChangeProvider={setActiveProvider}
        activeModel={activeModel}
        onChangeModel={setActiveModel}
        localGgufModel={localGgufModel}
        onSelectLocalGgufModel={setLocalGgufModel}
        onProviderConfigured={onProviderConfigured}
        onModelDeauthorized={onModelDeauthorized}
        ttsVoices={ttsVoices}
        onChangeTtsVoice={handleChangeTtsVoice}
        onChangeTtsProvider={handleChangeTtsProvider}
      />

      {/* DEVICE ASSISTANT MODAL */}
      <DeviceAssistantModal
        isOpen={isDeviceAssistantOpen}
        onClose={() => setIsDeviceAssistantOpen(false)}
        settings={settings}
        onUpdateSettings={(newSettings) =>
          setSettings((prev) => ({ ...prev, ...newSettings }))
        }
        onTriggerAssistant={() => {
          setIsDeviceAssistantOpen(false);
          startListening();
        }}
      />

      {/* DEVICE LINK HUB MODAL */}
      <DeviceLinkModal
        isOpen={isDeviceLinkOpen}
        onClose={() => setIsDeviceLinkOpen(false)}
        theme={settings.theme}
        onTaskDeferred={handleTaskDeferred}
      />

      {/* ONBOARDING MODAL - Hydration safe */}
      {isMounted && (
        <OnboardingModal
          isOpen={showOnboarding}
          onComplete={() => setDismissedOnboarding(true)}
          theme={settings.theme}
        />
      )}

      {/* DEVICE QUICK CONTROLS PANEL */}
      <DeviceControlPanel
        deviceState={deviceState}
        onUpdateState={(st) => setDeviceState((prev) => ({ ...prev, ...st }))}
        isOpen={isDeviceControlsOpen}
        onClose={() => setIsDeviceControlsOpen(false)}
      />

      {/* SCREEN CONTEXT SIMULATOR */}
      <ScreenContextSimulator
        isOpen={isScreenContextOpen}
        onClose={() => setIsScreenContextOpen(false)}
        onAttachContext={(contextText, title) => {
          setActiveScreenContext({ text: contextText, title });
          handleSendMessage(
            `I've attached my current screen: "${title}". Can you summarize it and highlight key items?`
          );
        }}
      />

      {/* "ASK WITH STELLA" FLOATING TEXT SELECTION MENU */}
      <AskWithStellaMenu
        enabled={settings.contextAwarenessEnabled}
        theme={settings.theme}
        onAsk={(action, selectedText) => {
          handleSendMessage(
            `[${action.toUpperCase()} THIS TEXT]: "${selectedText}"`
          );
        }}
      />

      {/* GOOGLE MAPS LOCATION & NAVIGATION MODAL */}
      <LocationMapsModal
        isOpen={isMapsOpen}
        onClose={() => setIsMapsOpen(false)}
        theme={settings.theme}
        initialQuery={mapsInitialQuery}
        initialRoute={mapsInitialRoute}
        initialMode={mapsInitialMode}
        onLocationSelect={(info) => {
          handleSendMessage(`Can you analyze this location or provide details: ${info}`);
        }}
      />
    </div>
  );
}


