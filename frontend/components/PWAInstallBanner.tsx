'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Download, X } from 'lucide-react';
import { THEME_CONFIGS } from '@/lib/theme';
import type { AssistantTheme } from '@/lib/types';

const DISMISSED_KEY = 'stella_pwa_install_dismissed';
const INSTALLED_KEY = 'stella_pwa_installed';

export interface PWAInstallBannerProps {
  theme: AssistantTheme;
  className?: string;
}

export function PWAInstallBanner({ theme, className }: PWAInstallBannerProps) {
  const [deferredPrompt, setDeferredPrompt] = useState<any | null>(null);
  const [showBanner, setShowBanner] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const config = THEME_CONFIGS[theme] || THEME_CONFIGS.void;

  // Check if already installed (standalone mode) or dismissed
  useEffect(() => {
    const isStandalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      (window.navigator as any).standalone === true;

    const dismissed = localStorage.getItem(DISMISSED_KEY) === 'true';
    const alreadyInstalled = localStorage.getItem(INSTALLED_KEY) === 'true';

    setIsInstalled(isStandalone || alreadyInstalled);

    // Only show if not installed and not dismissed
    if (!isStandalone && !alreadyInstalled && !dismissed) {
      setShowBanner(true);
    }
  }, []);

  // Listen for beforeinstallprompt
  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      if (!isInstalled) {
        setShowBanner(true);
      }
    };

    const handleAppInstalled = () => {
      setShowBanner(false);
      setIsInstalled(true);
      localStorage.setItem(INSTALLED_KEY, 'true');
      setDeferredPrompt(null);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, [isInstalled]);

  const handleInstall = useCallback(async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      localStorage.setItem(INSTALLED_KEY, 'true');
      setIsInstalled(true);
    }
    setDeferredPrompt(null);
    setShowBanner(false);
  }, [deferredPrompt]);

  const handleDismiss = useCallback(() => {
    localStorage.setItem(DISMISSED_KEY, 'true');
    setShowBanner(false);
    setDeferredPrompt(null);
  }, []);

  if (!showBanner || isInstalled) return null;

  return (
    <div
      className={`fixed bottom-4 left-4 right-4 sm:bottom-6 sm:left-6 sm:right-6 z-50 ${className}`}
      role="dialog"
      aria-modal="true"
      aria-label="Install Stella"
    >
      <div
        className={`flex items-center gap-3 px-4 py-3.5 rounded-2xl border shadow-xl transition-all duration-300 ${
          config.bgGlowGradient ? config.bgGlowGradient : 'bg-[#030509]'
        } border-slate-800/90`}
        style={{
          borderColor: config.primaryHex + '50',
          boxShadow: config.buttonShadow || 'shadow-[0_0_20px_rgba(0,0,0,0.4)]',
        }}
      >
        <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{
          background: config.buttonGradient || config.primaryHex,
          boxShadow: config.buttonShadow || 'shadow-[0_0_15px_rgba(0,229,163,0.4)]',
        }}>
          <Download className="w-5 h-5 text-[#030509]" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-bold text-slate-100 leading-tight">
            Install Stella
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
            Add Stella to your home screen for quick access and offline use.
          </p>
        </div>
        <div className="flex items-center gap-2 ml-2 shrink-0">
          <button
            type="button"
            onClick={handleInstall}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
              config.buttonGradient || config.primaryHex
            } text-[#030509] hover:opacity-90 active:scale-95`}
            aria-label="Install Stella app"
          >
            Install
          </button>
          <button
            type="button"
            onClick={handleDismiss}
            className="w-6 h-6 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 transition-colors flex items-center justify-center"
            aria-label="Dismiss install banner"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
