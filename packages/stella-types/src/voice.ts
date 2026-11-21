/**
 * @stella/types - Voice / TTS Types
 */

export type TTSProviderType = 'kokoro' | 'edge' | 'auto';

export interface TTSVoice {
  id: string;
  name: string;
  provider: TTSProviderType;
  gender: 'female' | 'male';
  language: string;
  description: string;
  active: boolean;
}

export interface TTSConfig {
  provider: TTSProviderType;
  voiceId: string;
  rate: number;
  pitch: number;
  autoSpeak: boolean;
}
