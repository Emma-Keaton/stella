import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        stella: {
          primary: 'var(--stella-primary)',
          secondary: 'var(--stella-secondary)',
          tertiary: 'var(--stella-tertiary)',
          quaternary: 'var(--stella-quaternary)',
          glow: 'var(--stella-glow)',
          'glow-secondary': 'var(--stella-glow-secondary)',
          bg: 'var(--stella-bg)',
          surface: 'var(--stella-surface)',
          'surface-raised': 'var(--stella-surface-raised)',
          glass: 'var(--stella-glass)',
          'glass-border': 'var(--stella-glass-border)',
          'text-primary': 'var(--stella-text-primary)',
          'text-secondary': 'var(--stella-text-secondary)',
          'text-muted': 'var(--stella-text-muted)',
          border: 'var(--stella-border)',
          'border-strong': 'var(--stella-border-strong)',
          success: 'var(--stella-success)',
          warning: 'var(--stella-warning)',
          error: 'var(--stella-error)',
        },
      },
      fontFamily: {
        display: ['var(--font-orbitron)', 'Orbitron', 'sans-serif'],
        sans: ['var(--font-exo)', 'Exo 2', 'sans-serif'],
        mono: ['var(--font-mono)', 'Fira Code', 'monospace'],
      },
      animation: {
        'soundwave': 'soundwave 0.8s ease-in-out infinite',
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'float': 'float 3s ease-in-out infinite',
        'rotate-slow': 'rotate-slow 20s linear infinite',
      },
      keyframes: {
        soundwave: {
          '0%, 100%': { height: '4px', opacity: '0.4' },
          '50%': { height: '24px', opacity: '1' },
        },
        'pulse-glow': {
          '0%, 100%': { opacity: '0.5' },
          '50%': { opacity: '1' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'rotate-slow': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;