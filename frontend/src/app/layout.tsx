import './globals.css';
import React from 'react';
import type { Metadata, Viewport } from 'next';

const SITE_NAME = 'AARK Kernel Control Center';

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'),
  title: {
    default: `${SITE_NAME} — Trading & Risk Platform`,
    template: `%s · ${SITE_NAME}`,
  },
  description:
    'Real-time trading dashboard with VaR/CVaR risk analytics, portfolio monitoring, position sizing and a secure exchange API-key vault.',
  applicationName: SITE_NAME,
  keywords: [
    'trading platform',
    'risk management',
    'VaR',
    'CVaR',
    'value at risk',
    'portfolio analytics',
    'crypto trading',
    'Nobitex',
  ],
  manifest: '/manifest.json',
  icons: {
    icon: [
      { url: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: [{ url: '/icon-192.png', sizes: '192x192', type: 'image/png' }],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: SITE_NAME,
  },
  openGraph: {
    type: 'website',
    siteName: SITE_NAME,
    title: `${SITE_NAME} — Trading & Risk Platform`,
    description:
      'Real-time trading dashboard with VaR/CVaR risk analytics, portfolio monitoring and a secure API-key vault.',
    images: [{ url: '/icon-512.png', width: 512, height: 512, alt: SITE_NAME }],
  },
  twitter: {
    card: 'summary',
    title: `${SITE_NAME} — Trading & Risk Platform`,
    description: 'Real-time trading dashboard with VaR/CVaR risk analytics and portfolio monitoring.',
    images: ['/icon-512.png'],
  },
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  themeColor: '#f4c85d',
  colorScheme: 'dark',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
