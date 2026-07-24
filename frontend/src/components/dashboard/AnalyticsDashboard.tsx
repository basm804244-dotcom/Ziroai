'use client';

import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, Users, MessageSquare, Zap, DollarSign } from 'lucide-react';

const usageData = [
  { name: 'Mon', tokens: 45000, cost: 2.3 },
  { name: 'Tue', tokens: 52000, cost: 2.8 },
  { name: 'Wed', tokens: 48000, cost: 2.5 },
  { name: 'Thu', tokens: 61000, cost: 3.2 },
  { name: 'Fri', tokens: 55000, cost: 2.9 },
  { name: 'Sat', tokens: 32000, cost: 1.6 },
  { name: 'Sun', tokens: 28000, cost: 1.4 },
];

const modelData = [
  { name: 'GPT-4o', value: 35, color: '#3b82f6' },
  { name: 'Claude 3.5', value: 25, color: '#8b5cf6' },
  { name: 'Gemini', value: 20, color: '#10b981' },
  { name: 'DeepSeek', value: 15, color: '#f59e0b' },
  { name: 'Others', value: 5, color: '#6b7280' },
];

const stats = [
  { label: 'Total Users', value: '12,847', icon: Users, change: '+12%' },
  { label: 'Messages Today', value: '45,231', icon: MessageSquare, change: '+8%' },
  { label: 'Tokens Used', value: '2.4M', icon: Zap, change: '+23%' },
  { label: 'Revenue', value: '$8,420', icon: DollarSign, change: '+15%' },
];

export function AnalyticsDashboard() {
  const [period, setPeriod] = useState('7d');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Analytics Dashboard</h1>
        <select value={period} onChange={(e) => setPeriod(e.target.value)} className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm">
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
        </select>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-gray-800/50 border border-gray-700 rounded-xl p-5">
              <div className="flex items-center justify-between">
                <Icon className="w-5 h-5 text-gray-400" />
                <span className="text-xs text-green-400 bg-green-400/10 px-2 py-0.5 rounded-full">{stat.change}</span>
              </div>
              <p className="text-2xl font-bold mt-2">{stat.value}</p>
              <p className="text-sm text-gray-400">{stat.label}</p>
            </div>
          );
        })}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4">Token Usage</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={usageData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
              <Bar dataKey="tokens" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4">Model Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={modelData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={5} dataKey="value">
                {modelData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap justify-center gap-3 mt-4">
            {modelData.map((m) => (
              <div key={m.name} className="flex items-center space-x-1">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: m.color }} />
                <span className="text-xs text-gray-400">{m.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold mb-4">Cost Trends</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={usageData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="name" stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" />
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
            <Line type="monotone" dataKey="cost" stroke="#10b981" strokeWidth={2} dot={{ fill: '#10b981' }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
