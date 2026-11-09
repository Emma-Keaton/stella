import { AssistantTheme } from './types';

export interface ThemeConfig {
  name: string;
  primaryHex: string;
  secondaryHex: string;
  tertiaryHex: string;
  quaternaryHex: string;
  glowRgba: string;
  secondaryGlowRgba: string;
  textAccentClass: string;
  borderAccentClass: string;
  bgSubtleClass: string;
  bgGlowGradient: string;
  buttonGradient: string;
  buttonShadow: string;
  gradientStops: [string, string, string, string];
}

export const THEME_CONFIGS: Record<AssistantTheme, ThemeConfig> = {
  rainbow: {
    name: 'Rainbow Aurora',
    primaryHex: '#00f0ff',
    secondaryHex: '#00ff88',
    tertiaryHex: '#ffd000',
    quaternaryHex: '#ff007f',
    glowRgba: 'rgba(0, 240, 255, 0.55)',
    secondaryGlowRgba: 'rgba(255, 0, 127, 0.45)',
    textAccentClass: 'text-[#00f0ff]',
    borderAccentClass: 'border-[#00f0ff]/40',
    bgSubtleClass: 'bg-[#00f0ff]/10',
    bgGlowGradient:
      'radial-gradient(ellipse at 50% -10%, rgba(0,240,255,0.22), rgba(217,70,239,0.15), rgba(0,255,136,0.08), transparent 70%)',
    buttonGradient:
      'bg-gradient-to-r from-[#00f0ff] via-[#00c8ff] to-[#0077ff] hover:from-[#38bdf8] hover:to-[#2563eb]',
    buttonShadow: 'shadow-[0_0_20px_rgba(0,240,255,0.35)]',
    gradientStops: ['#00f0ff', '#00ff88', '#ffd000', '#ff007f'],
  },
  nebula: {
    name: 'Deep Nebula',
    primaryHex: '#e879f9',
    secondaryHex: '#a855f7',
    tertiaryHex: '#6366f1',
    quaternaryHex: '#ec4899',
    glowRgba: 'rgba(232, 121, 249, 0.55)',
    secondaryGlowRgba: 'rgba(99, 102, 241, 0.45)',
    textAccentClass: 'text-[#e879f9]',
    borderAccentClass: 'border-[#e879f9]/40',
    bgSubtleClass: 'bg-[#e879f9]/10',
    bgGlowGradient:
      'radial-gradient(ellipse at 50% -10%, rgba(232,121,249,0.25), rgba(168,85,247,0.18), rgba(99,102,241,0.1), transparent 70%)',
    buttonGradient:
      'bg-gradient-to-r from-[#e879f9] via-[#a855f7] to-[#6366f1] hover:from-[#f0abfc] hover:to-[#818cf8]',
    buttonShadow: 'shadow-[0_0_20px_rgba(232,121,249,0.35)]',
    gradientStops: ['#e879f9', '#a855f7', '#6366f1', '#ec4899'],
  },
  cyan: {
    name: 'Cyber Cyan',
    primaryHex: '#00f0ff',
    secondaryHex: '#38bdf8',
    tertiaryHex: '#0284c7',
    quaternaryHex: '#2563eb',
    glowRgba: 'rgba(0, 240, 255, 0.65)',
    secondaryGlowRgba: 'rgba(37, 99, 235, 0.45)',
    textAccentClass: 'text-[#00f0ff]',
    borderAccentClass: 'border-[#00f0ff]/40',
    bgSubtleClass: 'bg-[#00f0ff]/10',
    bgGlowGradient:
      'radial-gradient(ellipse at 50% -10%, rgba(0,240,255,0.28), rgba(2,132,199,0.18), rgba(30,58,138,0.1), transparent 70%)',
    buttonGradient:
      'bg-gradient-to-r from-[#00f0ff] via-[#38bdf8] to-[#0284c7] hover:from-[#67e8f9] hover:to-[#0369a1]',
    buttonShadow: 'shadow-[0_0_20px_rgba(0,240,255,0.4)]',
    gradientStops: ['#67e8f9', '#00f0ff', '#0284c7', '#2563eb'],
  },
  solar: {
    name: 'Solar Flare',
    primaryHex: '#fbbf24',
    secondaryHex: '#fb8500',
    tertiaryHex: '#ff0054',
    quaternaryHex: '#ef4444',
    glowRgba: 'rgba(251, 191, 36, 0.6)',
    secondaryGlowRgba: 'rgba(255, 0, 84, 0.45)',
    textAccentClass: 'text-[#fbbf24]',
    borderAccentClass: 'border-[#fbbf24]/40',
    bgSubtleClass: 'bg-[#fbbf24]/10',
    bgGlowGradient:
      'radial-gradient(ellipse at 50% -10%, rgba(251,191,36,0.25), rgba(251,133,0,0.18), rgba(239,68,68,0.1), transparent 70%)',
    buttonGradient:
      'bg-gradient-to-r from-[#fbbf24] via-[#fb8500] to-[#ef4444] hover:from-[#fde047] hover:to-[#dc2626]',
    buttonShadow: 'shadow-[0_0_20px_rgba(251,191,36,0.4)]',
    gradientStops: ['#ffe600', '#fb8500', '#ff0054', '#ef4444'],
  },
};

// Helper function to dynamically bind theme CSS custom properties to documentElement
export function applyTheme(theme: AssistantTheme) {
  if (typeof window === 'undefined') return;
  const config = THEME_CONFIGS[theme] || THEME_CONFIGS.rainbow;
  const root = document.documentElement;

  root.style.setProperty('--stella-primary', config.primaryHex);
  root.style.setProperty('--stella-secondary', config.secondaryHex);
  root.style.setProperty('--stella-tertiary', config.tertiaryHex);
  root.style.setProperty('--stella-quaternary', config.quaternaryHex);
  root.style.setProperty('--stella-glow', config.glowRgba);
  root.style.setProperty('--stella-glow-secondary', config.secondaryGlowRgba);
  root.style.setProperty('--stella-bg-glow', config.bgGlowGradient);
  root.style.setProperty('--stella-stop-0', config.gradientStops[0]);
  root.style.setProperty('--stella-stop-1', config.gradientStops[1]);
  root.style.setProperty('--stella-stop-2', config.gradientStops[2]);
  root.style.setProperty('--stella-stop-3', config.gradientStops[3]);
}
