/**
 * @stella/types - Assistant Settings
 */

import { ID, JSONValue } from './entity';

export type AssistantTheme = 'void' | 'oled' | 'aurora' | 'light' | 'solar';
export type TTSProviderType = 'kokoro' | 'edge' | 'auto';

export interface AssistantSettings {
  id: ID;
  isDefaultAssistant: boolean;
  startListeningOnOpen: boolean;
  attachScreenshotOnInvoke: boolean;
  wakeWordEnabled: boolean;
  wakeWordPhrase: string;
  contextAwarenessEnabled: boolean;
  theme: AssistantTheme;
  animateBackground: boolean;
  voicePitch: number;
  voiceRate: number;
  autoSpeakResponse: boolean;
  autoRespondOnPause: boolean;
  pauseThresholdMs: number;
  soundEffects: boolean;
  hapticFeedback: boolean;
  ttsProvider: TTSProviderType;
  ttsVoiceId: string;
}
