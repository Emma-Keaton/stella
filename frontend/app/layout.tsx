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
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${orbitron.variable} ${exo2.variable} ${firaCode.variable}`}>
      <body suppressHydrationWarning className="font-sans">
        {children}
      </body>
    </html>
  );
}
