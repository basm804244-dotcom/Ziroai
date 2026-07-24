import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/providers';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata: Metadata = {
  title: 'AetherAI - The Ultimate AI Platform 2026',
  description: "The world's most advanced AI platform. Access all AI models, agents, and tools in one place.",
  keywords: ['AI', 'LLM', 'GPT', 'Claude', 'Gemini', 'agents', 'chatbot', 'machine learning', '2026'],
  authors: [{ name: 'AetherAI Team' }],
  openGraph: {
    title: 'AetherAI - The Ultimate AI Platform',
    description: 'Access all AI models, agents, and tools in one unified platform.',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased bg-gray-950 text-white`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
