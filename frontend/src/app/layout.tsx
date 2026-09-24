import './globals.css';
import React from 'react';

export const metadata = {
  title: 'AARK Kernel Control Center',
  description: 'Autonomous AI Quantitative Trading & Gold ERP Kernel',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
