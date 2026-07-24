'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, MessageSquare, Bot, Brain, Zap, Shield, Globe, ArrowRight, Check } from 'lucide-react';
import { useUserStore } from '@/store';

export function LandingPage() {
  const [email, setEmail] = useState('');
  const { setUser } = useUserStore();

  const features = [
    { icon: Brain, title: '50+ AI Models', description: 'Access GPT-4o, Claude, Gemini, Grok, Llama, DeepSeek, and more.' },
    { icon: Bot, title: 'AI Agents', description: 'Pre-built agents for programming, medicine, law, data science.' },
    { icon: MessageSquare, title: 'Real-time Chat', description: 'Streaming responses with WebSocket support.' },
    { icon: Zap, title: 'Long-term Memory', description: 'Persistent memory with vector search and knowledge bases.' },
    { icon: Shield, title: 'Enterprise Security', description: 'OAuth2, MFA, WebAuthn, RBAC, audit logs.' },
    { icon: Globe, title: 'Multi-Platform', description: 'Web, Android, iOS, Windows, macOS, Linux.' },
  ];

  const models = ['GPT-4o', 'Claude 3.5', 'Gemini 1.5 Pro', 'Grok-2', 'DeepSeek-V3', 'Llama 3.3', 'Mistral Large', 'Command R+'];

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <section className="relative overflow-hidden pt-20 pb-32">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-900/20 via-gray-950 to-gray-950" />
        <div className="relative max-w-7xl mx-auto px-6 text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <div className="inline-flex items-center space-x-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5 mb-8">
              <Sparkles className="w-4 h-4 text-blue-400" />
              <span className="text-sm text-blue-400">Ultimate Edition 2026</span>
            </div>
            <h1 className="text-5xl md:text-7xl font-bold mb-6">
              The World&apos;s <span className="bg-gradient-to-r from-blue-400 via-purple-500 to-pink-500 bg-clip-text text-transparent">Most Advanced</span> AI Platform
            </h1>
            <p className="text-xl text-gray-400 max-w-3xl mx-auto mb-10">
              Access all AI models, agents, and tools in one unified platform. Built for developers, enterprises, and power users.
            </p>
          </motion.div>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="flex flex-wrap justify-center gap-3 mb-12">
            {models.map((model) => (
              <span key={model} className="bg-gray-800/50 border border-gray-700 rounded-full px-4 py-2 text-sm text-gray-300">{model}</span>
            ))}
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button onClick={() => setUser({ id: 'demo', email: 'demo@aether.ai', username: 'demo', full_name: 'Demo User', role: 'user', plan: 'free' })}
              className="bg-blue-500 hover:bg-blue-600 text-white px-8 py-4 rounded-xl font-semibold flex items-center space-x-2 transition-colors">
              <span>Get Started Free</span><ArrowRight className="w-5 h-5" />
            </button>
            <button className="bg-gray-800 hover:bg-gray-700 text-white px-8 py-4 rounded-xl font-semibold transition-colors">View Documentation</button>
          </motion.div>
        </div>
      </section>

      <section className="py-20 bg-gray-900/50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold mb-4">Everything You Need</h2>
            <p className="text-gray-400">A complete AI platform with enterprise-grade features</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <motion.div key={feature.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.1 }} viewport={{ once: true }}
                  className="bg-gray-800/50 border border-gray-700 rounded-2xl p-6 hover:border-blue-500/50 transition-colors">
                  <Icon className="w-10 h-10 text-blue-400 mb-4" />
                  <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                  <p className="text-gray-400">{feature.description}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold mb-4">Simple Pricing</h2>
            <p className="text-gray-400">Start free, scale as you grow</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              { name: 'Free', price: '$0', features: ['10K tokens/day', '3 agents', 'Basic memory', 'Community support'] },
              { name: 'Pro', price: '$29/mo', features: ['1M tokens/day', '20 agents', 'Advanced memory', 'Priority support', 'API access'], popular: true },
              { name: 'Enterprise', price: '$299/mo', features: ['Unlimited tokens', 'Unlimited agents', 'Custom models', 'SSO & SAML', 'Dedicated support', 'SLA guarantee'] },
            ].map((plan) => (
              <div key={plan.name} className={`rounded-2xl p-8 border ${plan.popular ? 'border-blue-500 bg-blue-500/5' : 'border-gray-700 bg-gray-800/50'}`}>
                {plan.popular && <span className="bg-blue-500 text-white text-xs font-semibold px-3 py-1 rounded-full">Most Popular</span>}
                <h3 className="text-2xl font-bold mt-4">{plan.name}</h3>
                <p className="text-4xl font-bold mt-2">{plan.price}</p>
                <ul className="mt-6 space-y-3">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center text-gray-300"><Check className="w-4 h-4 text-green-400 mr-2" />{f}</li>
                  ))}
                </ul>
                <button onClick={() => setUser({ id: 'demo', email: 'demo@aether.ai', username: 'demo', full_name: 'Demo User', role: 'user', plan: plan.name.toLowerCase() })}
                  className={`w-full mt-8 py-3 rounded-xl font-semibold transition-colors ${plan.popular ? 'bg-blue-500 hover:bg-blue-600 text-white' : 'bg-gray-700 hover:bg-gray-600 text-white'}`}>
                  Get Started
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="py-12 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-6 text-center text-gray-500">
          <p>&copy; 2026 AetherAI. Built with &hearts; for the AI community.</p>
        </div>
      </footer>
    </div>
  );
}
