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
    quaternaryHex: '#FF007F',
    glowRgba: 'rgba(0, 229, 163, 0.55)',
    secondaryGlowRgba: 'rgba(255, 0, 127, 0.45)',
    textAccentClass: 'text-[#00E5A3]',
    borderAccentClass: 'border-[#00E5A3]/40',
    bgSubtleClass: 'bg-[#00E5A3]/10',
    bgGlowGradient:
      'radial-gradient(ellipse at 50% -10%, rgba(0,229,163,0.22), rgba(217,70,239,0.15), rgba(0,255,136,0.08), transparent 70%)',
    buttonGradient:
      'bg-gradient-to-r from-[#00E5A3] via-[#00B8D4] to-[#6C5EE0] hover:from-[#10B981] hover:to-[#7C3AED]',
    buttonShadow: 'shadow-[0_0_20px_rgba(0,229,163,0.35)]',
    gradientStops: ['#00E5A3', '#00F0FF', '#8D80F0', '#FF007F'],
  },
  oled: {
    name: 'OLED True Black',
    primaryHex: '#00E5A3',
    secondaryHex: '#00F0FF',
    tertiaryHex: '#8D80F0',
    quaternaryHex: '#FF007F',
    glowRgba: 'rgba(0, 229, 163, 0.45)',
    secondaryGlowRgba: 'rgba(255, 0, 127, 0.35)',
    textAccentClass: 'text-[#00E5A3]',
    borderAccentClass: 'border-[#00E5A3]/40',
    bgSubtleClass: 'bg-[#00E5A3]/10',
    bgGlowGradient:
      'radial-gradient(ellipse at 50% -10%, rgba(0,229,163,0.15), rgba(217,70,239,0.08), rgba(0,255,136,0.05), transparent 70%)',
    buttonGradient:
      'bg-gradient-to-r from-[#00E5A3] via-[#00B8D4] to-[#6C5EE0] hover:from-[#10B981] hover:to-[#7C3AED]',
    buttonShadow: 'shadow-[0_0_15px_rgba(0,229,163,0.25)]',
    gradientStops: ['#00E5A3', '#00F0FF', '#8D80F0', '#FF007F'],
  },
  aurora: {
    name: 'Aurora',
    primaryHex: '#6C5EE0',
    secondaryHex: '#8D80F0',
    tertiaryHex: '#00E5A3',
    quaternaryHex: '#00F0FF',
    glowRgba: 'rgba(108, 94, 224, 0.55)',
    secondaryGlowRgba: 'rgba(99, 102, 241, 0.45)',
    textAccentClass: 'text-[#6C5EE0]',
    borderAccentClass: 'border-[#6C5EE0]/40',
    bgSubtleClass: 'bg-[#6C5EE0]/10',
    bgGlowGradient:
      'radial-gradient(ellipse at 50% -10%, rgba(108,94,224,0.25), rgba(141,128,240,0.18), rgba(99,102,241,0.1), transparent 70%)',
    buttonGradient:
      'bg-gradient-to-r from-[#6C5EE0] via-[#8D80F0] to-[#00E5A3] hover:from-[#818CF8] hover:to-[#10B981]',
    buttonShadow: 'shadow-[0_0_20px_rgba(108,94,224,0.35)]',
    gradientStops: ['#6C5EE0', '#8D80F0', '#00E5A3', '#00F0FF'],
  },
  solar: {
    name: 'Solar Flare',
    primaryHex: '#FBBF24',
    secondaryHex: '#FB8500',
    tertiaryHex: '#EF4444',
    quaternaryHex: '#F97316',
    glowRgba: 'rgba(251, 191, 36, 0.55)',
    secondaryGlowRgba: 'rgba(239, 68, 68, 0.45)',
    textAccentClass: 'text-[#FBBF24]',
    borderAccentClass: 'border-[#FBBF24]/40',
    bgSubtleClass: 'bg-[#FBBF24]/10',
    bgGlowGradient:
      'radial-gradient(ellipse at 50% -10%, rgba(251,191,36,0.25), rgba(251,133,0,0.18), rgba(239,68,68,0.1), transparent 70%)',
    buttonGradient:
      'bg-gradient-to-r from-[#FBBF24] via-[#FB8500] to-[#EF4444] hover:from-[#FDE047] hover:to-[#DC2626]',
    buttonShadow: 'shadow-[0_0_20px_rgba(251,191,36,0.4)]',
    gradientStops: ['#FBBF24', '#FB8500', '#EF4444', '#F97316'],
  },
  light: {
    name: 'Light',
    primaryHex: '#007A57',
    secondaryHex: '#007C8A',
    tertiaryHex: '#5A4BD1',
    quaternaryHex: '#EF4444',
    glowRgba: 'rgba(0, 122, 87, 0.35)',
    secondaryGlowRgba: 'rgba(0, 124, 138, 0.35)',
    textAccentClass: 'text-[#007A57]',
    borderAccentClass: 'border-[#007A57]/40',
    bgSubtleClass: 'bg-[#007A57]/10',
    bgGlowGradient: 'none',
    buttonGradient:
      'bg-gradient-to-r from-[#007A57] via-[#007C8A] to-[#5A4BD1] hover:from-[#006B4A] hover:to-[#4A3FC9]',
    buttonShadow: 'shadow-[0_0_15px_rgba(0,122,87,0.25)]',
    gradientStops: ['#007A57', '#007C8A', '#5A4BD1', '#EF4444'],
  },
};

export type { AssistantTheme };

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