'use client';

import { useState } from 'react';
import { Shield, Users, Settings, Activity, CheckCircle } from 'lucide-react';

export function AdminConsole() {
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'system'>('overview');

  const systemStatus = {
    services: [
      { name: 'API Gateway', status: 'healthy', uptime: '99.99%' },
      { name: 'Auth Service', status: 'healthy', uptime: '99.98%' },
      { name: 'Chat Service', status: 'healthy', uptime: '99.97%' },
      { name: 'Agent Service', status: 'healthy', uptime: '99.95%' },
      { name: 'Model Service', status: 'healthy', uptime: '99.99%' },
      { name: 'Memory Service', status: 'healthy', uptime: '99.96%' },
      { name: 'RAG Service', status: 'healthy', uptime: '99.94%' },
    ],
    databases: [
      { name: 'PostgreSQL', status: 'healthy', connections: 45 },
      { name: 'Redis', status: 'healthy', memory: '1.2GB' },
      { name: 'Qdrant', status: 'healthy', vectors: '2.1M' },
      { name: 'Neo4j', status: 'healthy', nodes: '500K' },
    ],
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Admin Console</h1>

      <div className="flex space-x-4 border-b border-gray-800">
        {[
          { id: 'overview', label: 'Overview', icon: Activity },
          { id: 'users', label: 'Users', icon: Users },
          { id: 'system', label: 'System', icon: Settings },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button key={tab.id} onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors ${activeTab === tab.id ? 'border-blue-500 text-blue-400' : 'border-transparent text-gray-400 hover:text-white'}`}>
              <Icon className="w-4 h-4" /><span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {activeTab === 'overview' && (
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'Total Users', value: '12,847', icon: Users },
            { label: 'Active Sessions', value: '1,234', icon: Activity },
            { label: 'API Requests/hr', value: '45.2K', icon: Shield },
            { label: 'System Health', value: '99.97%', icon: CheckCircle, color: 'text-green-400' },
          ].map((stat) => {
            const Icon = stat.icon;
            return (
              <div key={stat.label} className="bg-gray-800/50 border border-gray-700 rounded-xl p-5">
                <Icon className={`w-6 h-6 ${stat.color || 'text-blue-400'} mb-3`} />
                <p className="text-2xl font-bold">{stat.value}</p>
                <p className="text-sm text-gray-400">{stat.label}</p>
              </div>
            );
          })}
        </div>
      )}

      {activeTab === 'system' && (
        <div className="space-y-6">
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Services</h3>
            <div className="space-y-3">
              {systemStatus.services.map((svc) => (
                <div key={svc.name} className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0">
                  <div className="flex items-center space-x-3">
                    <div className={`w-2 h-2 rounded-full ${svc.status === 'healthy' ? 'bg-green-400' : 'bg-red-400'}`} />
                    <span>{svc.name}</span>
                  </div>
                  <span className="text-sm text-gray-400">{svc.uptime}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Databases</h3>
            <div className="space-y-3">
              {systemStatus.databases.map((db) => (
                <div key={db.name} className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0">
                  <div className="flex items-center space-x-3">
                    <div className="w-2 h-2 rounded-full bg-green-400" />
                    <span>{db.name}</span>
                  </div>
                  <span className="text-sm text-gray-400">{'connections' in db ? `${db.connections} conn` : db.memory || db.vectors}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'users' && (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-900">
              <tr>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-400">User</th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-400">Plan</th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-400">Status</th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-400">Joined</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {[
                { name: 'John Doe', email: 'john@example.com', plan: 'Pro', status: 'active', joined: '2026-01-15' },
                { name: 'Jane Smith', email: 'jane@example.com', plan: 'Enterprise', status: 'active', joined: '2026-02-20' },
                { name: 'Bob Wilson', email: 'bob@example.com', plan: 'Free', status: 'suspended', joined: '2026-03-10' },
              ].map((user) => (
                <tr key={user.email} className="hover:bg-gray-700/50">
                  <td className="px-6 py-4">
                    <div><p className="font-medium">{user.name}</p><p className="text-sm text-gray-400">{user.email}</p></div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`text-xs px-2 py-1 rounded-full ${user.plan === 'Enterprise' ? 'bg-purple-500/20 text-purple-400' : user.plan === 'Pro' ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-500/20 text-gray-400'}`}>{user.plan}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`text-xs px-2 py-1 rounded-full ${user.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>{user.status}</span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-400">{user.joined}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
