'use client';

import { useUIStore, useUserStore } from '@/store';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { AgentPanel } from '@/components/agents/AgentPanel';
import { AnalyticsDashboard } from '@/components/dashboard/AnalyticsDashboard';
import { AdminConsole } from '@/components/admin/AdminConsole';
import { MarketplaceView } from '@/components/marketplace/MarketplaceView';
import { WorkspaceIDE } from '@/components/workspace/WorkspaceIDE';
import { MessageSquare, Bot, BarChart3, Settings, ShoppingBag, Code2, Menu, X, LogOut, User, Sparkles, Moon, Sun } from 'lucide-react';

export function DashboardLayout() {
  const { activeTab, setActiveTab, sidebarOpen, toggleSidebar, theme, setTheme } = useUIStore();
  const { user, logout } = useUserStore();

  const tabs = [
    { id: 'chat', label: 'Chat', icon: MessageSquare, color: 'text-blue-400' },
    { id: 'agents', label: 'Agents', icon: Bot, color: 'text-purple-400' },
    { id: 'workspace', label: 'Workspace', icon: Code2, color: 'text-green-400' },
    { id: 'marketplace', label: 'Marketplace', icon: ShoppingBag, color: 'text-orange-400' },
    { id: 'analytics', label: 'Analytics', icon: BarChart3, color: 'text-pink-400' },
    { id: 'admin', label: 'Admin', icon: Settings, color: 'text-gray-400' },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'chat': return <ChatPanel />;
      case 'agents': return <AgentPanel />;
      case 'workspace': return <WorkspaceIDE />;
      case 'marketplace': return <MarketplaceView />;
      case 'analytics': return <AnalyticsDashboard />;
      case 'admin': return <AdminConsole />;
      default: return <ChatPanel />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
      <aside className={`${sidebarOpen ? 'w-64' : 'w-16'} bg-gray-900 border-r border-gray-800 transition-all duration-300 flex flex-col`}>
        <div className="h-16 flex items-center px-4 border-b border-gray-800">
          <Sparkles className="w-8 h-8 text-blue-500" />
          {sidebarOpen && <span className="ml-3 text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">AetherAI</span>}
        </div>
        <nav className="flex-1 py-4 space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center px-4 py-3 transition-colors ${isActive ? 'bg-blue-500/10 border-r-2 border-blue-500' : 'hover:bg-gray-800'}`}>
                <Icon className={`w-5 h-5 ${isActive ? tab.color : 'text-gray-400'}`} />
                {sidebarOpen && <span className={`ml-3 ${isActive ? 'text-white font-medium' : 'text-gray-400'}`}>{tab.label}</span>}
              </button>
            );
          })}
        </nav>
        <div className="p-4 border-t border-gray-800 space-y-2">
          <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} className="w-full flex items-center px-2 py-2 text-gray-400 hover:text-white transition-colors">
            {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            {sidebarOpen && <span className="ml-3">{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>}
          </button>
          <button onClick={logout} className="w-full flex items-center px-2 py-2 text-red-400 hover:text-red-300 transition-colors">
            <LogOut className="w-5 h-5" />
            {sidebarOpen && <span className="ml-3">Logout</span>}
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-6">
          <button onClick={toggleSidebar} className="text-gray-400 hover:text-white">
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 bg-gray-800 rounded-full px-4 py-1.5">
              <User className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-300">{user?.full_name || 'Guest'}</span>
              <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full">{user?.plan || 'Free'}</span>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">{renderContent()}</main>
      </div>
    </div>
  );
}
