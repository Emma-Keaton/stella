import type { Metadata } from 'next';
import { Orbitron, Exo_2, Fira_Code } from 'next/font/google';
import './globals.css';

const orbitron = Orbitron({
  subsets: ['latin'],
  variable: '--font-orbitron',
  display: 'swap',
});

const exo2 = Exo_2({
  subsets: ['latin'],
  variable: '--font-exo',
  display: 'swap',
});

const firaCode = Fira_Code({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Stella - Futuristic AI Voice & Device Assistant',
  description:
    'Your AI assistant that molds to your workflow, voice, and daily needs.',
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon.ico',
    apple: '/favicon.ico',
  },
  openGraph: {
    title: 'Stella - Futuristic AI Voice & Device Assistant',
    description:
      'Your AI assistant that molds to your workflow, voice, and daily needs.',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Stella - Futuristic AI Voice & Device Assistant',
    description:
      'Your AI assistant that molds to your workflow, voice, and daily needs.',
  },
  manifest: '/manifest.json',
  colorScheme: 'dark',
  themeColor: '#00E5A3',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${orbitron.variable} ${exo2.variable} ${firaCode.variable}`}
    >
      <body
        suppressHydrationWarning
        className="font-sans"
      >
        {/* PWA Meta Tags */}
        <meta name="theme-color" content="#00E5A3" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black" />
        <meta name="apple-mobile-web-app-title" content="Stella" />
        <meta name="application-name" content="Stella" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="msapplication-TileColor" content="#00E5A3" />
        <meta name="msapplication-TileImage" content="/favicon.ico" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" sizes="180x180" href="/assets/stella/stella_icon_256.png" />
        <link rel="icon" type="image/x-icon" href="/favicon.ico" />

        {children}

        {/* Service Worker Registration */}
        <script
          id="stella-sw-register"
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => {
                  navigator.serviceWorker.register('/sw.js', { scope: '/' })
                    .then((reg) => {
                      console.log('[Stella PWA] Service Worker registered:', reg.scope);
                      if (reg.waiting) {
                        reg.waiting.postMessage({ type: 'SKIP_WAITING' });
                      }
                    })
                    .catch((err) => {
                      console.warn('[Stella PWA] Service Worker registration failed:', err);
                    });
                });
              }
            `,
          }}
        />
      </body>
    </html>
  );
}
