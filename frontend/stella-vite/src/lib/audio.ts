// Audio utilities for Stella
class SoundManager {
  private audioContext: AudioContext | null = null;
  private sounds: Map<string, AudioBuffer> = new Map();

  private getContext(): AudioContext {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
    return this.audioContext;
  }

  private createTone(frequency: number, duration: number, type: OscillatorType = 'sine', volume: number = 0.3): AudioBuffer {
    const ctx = this.getContext();
    const sampleRate = ctx.sampleRate;
    const length = sampleRate * duration;
    const buffer = ctx.createBuffer(1, length, sampleRate);
    const data = buffer.getChannelData(0);

    for (let i = 0; i < length; i++) {
      const t = i / sampleRate;
      const envelope = Math.exp(-t * 3);
      let sample = 0;
      if (type === 'sine') {
        sample = Math.sin(2 * Math.PI * frequency * t);
      } else if (type === 'square') {
        sample = Math.sign(Math.sin(2 * Math.PI * frequency * t));
      } else if (type === 'triangle') {
        sample = (2 / Math.PI) * Math.asin(Math.sin(2 * Math.PI * frequency * t));
      }
      data[i] = sample * envelope * volume;
    }
    return buffer;
  }

  private playBuffer(buffer: AudioBuffer, volume: number = 1) {
    const ctx = this.getContext();
    const source = ctx.createBufferSource();
    const gainNode = ctx.createGain();
    source.buffer = buffer;
    gainNode.gain.value = volume;
    source.connect(gainNode);
    gainNode.connect(ctx.destination);
    source.start(0);
  }

  playListeningStart() {
    const ctx = this.getContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1320, ctx.currentTime + 0.15);
    gain.gain.setValueAtTime(0.2, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.2);
  }

  playListeningEnd() {
    const ctx = this.getContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(1320, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15);
    gain.gain.setValueAtTime(0.2, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.2);
  }

  playActionChime() {
    const ctx = this.getContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(523.25, ctx.currentTime);
    osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.1);
    osc.frequency.setValueAtTime(783.99, ctx.currentTime + 0.2);
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.4);
  }

  playError() {
    const ctx = this.getContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'square';
    osc.frequency.setValueAtTime(300, ctx.currentTime);
    osc.frequency.setValueAtTime(200, ctx.currentTime + 0.1);
    osc.frequency.setValueAtTime(150, ctx.currentTime + 0.2);
    gain.gain.setValueAtTime(0.2, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.3);
  }

  playSuccess() {
    const ctx = this.getContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(523.25, ctx.currentTime);
    osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.08);
    osc.frequency.setValueAtTime(783.99, ctx.currentTime + 0.16);
    osc.frequency.setValueAtTime(1046.5, ctx.currentTime + 0.24);
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.4);
  }
}

export const sounds = new SoundManager();

let speechSynthesis: SpeechSynthesis | null = null;
if (typeof window !== 'undefined') {
  speechSynthesis = window.speechSynthesis;
}

export function speakText(text: string, lang: string = 'en-US', rate: number = 1, pitch: number = 1) {
  if (!speechSynthesis) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.rate = rate;
  utterance.pitch = pitch;
  utterance.volume = 0.8;
  speechSynthesis.speak(utterance);
}

export function stopSpeaking() {
  if (speechSynthesis) {
    speechSynthesis.cancel();
  }
}

export function startRecording(onData: (blob: Blob) => void, onEnd: () => void): MediaRecorder | null {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices) return null;
  return null;
}

export function stopRecording(recorder: MediaRecorder | null) {
  if (recorder && recorder.state === 'recording') {
    recorder.stop();
  }
}