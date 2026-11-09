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
  void: {
    name: 'Void',
    primaryHex: '#00E5A3',
    secondaryHex: '#00F0FF',
    tertiaryHex: '#8D80F0',
    quaternaryHex: '#00F0FF',
    glowRgba: 'rgba(0, 240, 255, 0.35)',
    secondaryGlowRgba: 'rgba(141, 128, 240, 0.35)',
    textAccentClass: 'text-[#00E5A3]',
    borderAccentClass: 'border-[#00E5A3]/40',
    bgSubtleClass: 'bg-[#00E5A3]/10',
    bgGlowGradient:
      'radial-gradient(ellipse at 50% -10%, rgba(0,240,255,0.35), rgba(141,128,240,0.15), rgba(0,229,163,0.08), transparent 70%)',
    buttonGradient:
      'bg-gradient-to-r from-[#00E5A3] via-[#00F0FF] to-[#8D80F0] hover:from-[#38bdf8] hover:to-[#2563eb]',
    buttonShadow: 'shadow-[0_0_20px_rgba(0,229,163,0.35)]',
    gradientStops: ['#00E5A3', '#00F0FF', '#8D80F0', '#00F0FF'],
  },
  oled: {
    name: 'OLED True Black',
    primaryHex: '#00E5A3',
    secondaryHex: '#00F0FF',
    tertiaryHex: '#8D80F0',
    quaternaryHex: '#00F0FF',
    glowRgba: 'rgba(0, 240, 255, 0.45)',
    secondaryGlowRgba: 'rgba(141, 128, 240, 0.35)',
    textAccentClass: 'text-[#00E5A3]',
    borderAccentClass: 'border-[#00E5A3]/40',
    bgSubtleClass: 'bg-[#00E5A3]/10',
    bgGlowGradient:
      'radial-gradient(ellipse at 50% -10%, rgba(0,240,255,0.45), rgba(141,128,240,0.18), rgba(0,229,163,0.1), transparent 70%)',
    buttonGradient:
      'bg-gradient-to-r from-[#00E5A3] via-[#00F0FF] to-[#8D80F0] hover:from-[#38bdf8] hover:to-[#2563eb]',
    buttonShadow: 'shadow-[0_0_24px_rgba(0,229,163,0.5)]',
    gradientStops: ['#00E5A3', '#00F0FF', '#8D80F0', '#00F0FF'],
  },
  aurora: {
    name: 'Aurora',
    primaryHex: '#8D80F0',
    secondaryHex: '#8D80F0',
    tertiaryHex: '#8D80F0',
    quaternaryHex: '#8D80F0',
    glowRgba: 'rgba(141, 128, 240, 0.35)',
    secondaryGlowRgba: 'rgba(232, 121, 249, 0.35)',
    textAccentClass: 'text-[#8D80F0]',
    borderAccentClass: 'border-[#8D80F0]/40',
    bgSubtleClass: 'bg-[#8D80F0]/10',
    bgGlowGradient:
      'radial-gradient(ellipse at 50% -10%, rgba(141,128,240,0.35), rgba(232,121,249,0.15), rgba(0,229,163,0.08), transparent 70%)',
    buttonGradient:
      'bg-gradient-to-r from-[#8D80F0] via-[#a855f7] to-[#e879f9] hover:from-[#818cf8] hover:to-[#a78bfa]',
    buttonShadow: 'shadow-[0_0_20px_rgba(141,128,240,0.35)]',
    gradientStops: ['#8D80F0', '#a855f7', '#e879f9', '#8D80F0'],
  },
  light: {
    name: 'Light',
    primaryHex: '#007A57',
    secondaryHex: '#007C8A',
    tertiaryHex: '#5A4BD1',
    quaternaryHex: '#007C8A',
    glowRgba: 'none',
    secondaryGlowRgba: 'none',
    textAccentClass: 'text-[#007A57]',
    borderAccentClass: 'border-[#007A57]/40',
    bgSubtleClass: 'bg-[#007A57]/10',
    bgGlowGradient: 'none',
    buttonGradient:
      'bg-gradient-to-r from-[#007A57] via-[#007C8A] to-[#5A4BD1] hover:from-[#059669] hover:to-[#4f46e5]',
    buttonShadow: 'shadow-[0_0_12px_rgba(0,122,87,0.2)]',
    gradientStops: ['#007A57', '#007C8A', '#5A4BD1', '#007C8A'],
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
  const config = THEME_CONFIGS[theme] || THEME_CONFIGS.void;
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
