'use client';

import { useState } from 'react';
import { ShoppingBag, Star, Download, Search } from 'lucide-react';

const PLUGINS = [
  { id: '1', name: 'PDF Analyzer', author: 'AetherAI', rating: 4.8, downloads: 12500, category: 'Document', price: 'Free', icon: '📄' },
  { id: '2', name: 'Code Reviewer', author: 'DevTools', rating: 4.9, downloads: 8900, category: 'Development', price: 'Free', icon: '🔍' },
  { id: '3', name: 'SQL Assistant', author: 'DataTeam', rating: 4.7, downloads: 6700, category: 'Database', price: '$9/mo', icon: '🗄️' },
  { id: '4', name: 'Image Generator Pro', author: 'CreativeAI', rating: 4.6, downloads: 15200, category: 'Image', price: '$19/mo', icon: '🎨' },
  { id: '5', name: 'Meeting Summarizer', author: 'Productivity', rating: 4.8, downloads: 9800, category: 'Productivity', price: 'Free', icon: '📝' },
  { id: '6', name: 'Legal Document AI', author: 'LawTech', rating: 4.5, downloads: 3400, category: 'Legal', price: '$49/mo', icon: '⚖️' },
];

const AGENTS = [
  { id: 'a1', name: 'SEO Expert', author: 'MarketingPro', rating: 4.9, uses: 45000, category: 'Marketing', icon: '📈' },
  { id: 'a2', name: 'Bug Hunter', author: 'Securify', rating: 4.7, uses: 12000, category: 'Security', icon: '🐛' },
  { id: 'a3', name: 'Data Viz Master', author: 'AnalyticsHub', rating: 4.8, uses: 28000, category: 'Data', icon: '📊' },
];

export function MarketplaceView() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [tab, setTab] = useState<'plugins' | 'agents'>('plugins');

  const items = tab === 'plugins' ? PLUGINS : AGENTS;
  const filtered = items.filter((item) => {
    const matchesSearch = item.name.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = category === 'all' || item.category === category;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Marketplace</h1>
        <div className="flex space-x-2">
          <button onClick={() => setTab('plugins')} className={`px-4 py-2 rounded-lg ${tab === 'plugins' ? 'bg-blue-500 text-white' : 'bg-gray-800 text-gray-400'}`}>Plugins</button>
          <button onClick={() => setTab('agents')} className={`px-4 py-2 rounded-lg ${tab === 'agents' ? 'bg-blue-500 text-white' : 'bg-gray-800 text-gray-400'}`}>Agents</button>
        </div>
      </div>

      <div className="flex space-x-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search marketplace..." className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-blue-500" />
        </div>
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2">
          <option value="all">All Categories</option>
          <option value="Document">Document</option>
          <option value="Development">Development</option>
          <option value="Database">Database</option>
          <option value="Image">Image</option>
          <option value="Productivity">Productivity</option>
          <option value="Marketing">Marketing</option>
        </select>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((item) => (
          <div key={item.id} className="bg-gray-800/50 border border-gray-700 rounded-xl p-5 hover:border-blue-500/50 transition-colors">
            <div className="flex items-start justify-between">
              <div className="text-3xl">{item.icon}</div>
              <span className={`text-xs px-2 py-1 rounded-full ${item.price === 'Free' ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'}`}>{item.price}</span>
            </div>
            <h3 className="font-semibold mt-3">{item.name}</h3>
            <p className="text-sm text-gray-400">by {item.author}</p>
            <div className="flex items-center mt-3 space-x-4 text-xs text-gray-500">
              <span className="flex items-center"><Star className="w-3 h-3 text-yellow-400 mr-1" />{item.rating}</span>
              <span className="flex items-center">{tab === 'plugins' ? <Download className="w-3 h-3 mr-1" /> : <ShoppingBag className="w-3 h-3 mr-1" />}{tab === 'plugins' ? item.downloads?.toLocaleString() : item.uses?.toLocaleString()}</span>
            </div>
            <button className="w-full mt-4 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg text-sm font-medium transition-colors">Install</button>
          </div>
        ))}
      </div>
    </div>
  );
}
