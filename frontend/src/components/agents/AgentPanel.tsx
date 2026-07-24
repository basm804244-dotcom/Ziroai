'use client';

import { useState } from 'react';
import { useAgentStore } from '@/store';
import { Bot, Plus, Star, Play, Settings } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const TEMPLATES = [
  { id: 'doctor', name: 'AI Doctor', desc: 'Medical consultation', color: 'bg-red-500/20 text-red-400' },
  { id: 'lawyer', name: 'AI Lawyer', desc: 'Legal consultation', color: 'bg-amber-500/20 text-amber-400' },
  { id: 'programmer', name: 'Code Master', desc: 'Programming expert', color: 'bg-blue-500/20 text-blue-400' },
  { id: 'translator', name: 'Translator', desc: '100+ languages', color: 'bg-green-500/20 text-green-400' },
  { id: 'data_scientist', name: 'Data Scientist', desc: 'ML & Analytics', color: 'bg-purple-500/20 text-purple-400' },
  { id: 'creative_writer', name: 'Creative Writer', desc: 'Content creation', color: 'bg-pink-500/20 text-pink-400' },
  { id: 'financial_advisor', name: 'Financial Advisor', desc: 'Investment advice', color: 'bg-emerald-500/20 text-emerald-400' },
  { id: 'teacher', name: 'AI Teacher', desc: 'Personal tutor', color: 'bg-indigo-500/20 text-indigo-400' },
  { id: 'cybersecurity', name: 'Security Expert', desc: 'Cybersecurity', color: 'bg-rose-500/20 text-rose-400' },
  { id: 'devops', name: 'DevOps Engineer', desc: 'Infrastructure', color: 'bg-cyan-500/20 text-cyan-400' },
];

export function AgentPanel() {
  const { agents, selectedAgent, selectAgent, addAgent } = useAgentStore();
  const [activeTab, setActiveTab] = useState<'browse' | 'create' | 'execute'>('browse');
  const [newAgent, setNewAgent] = useState({ name: '', description: '', system_prompt: '', model_id: 'gpt-4o' });
  const [executeInput, setExecuteInput] = useState('');
  const [executeResult, setExecuteResult] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);

  const createFromTemplate = (templateId: string) => {
    const t = TEMPLATES.find((x) => x.id === templateId);
    if (!t) return;
    const agent = { id: Date.now().toString(), name: t.name, description: t.desc, type: 'prebuilt', model_id: 'gpt-4o', system_prompt: `You are a ${t.name}.`, tools: [], knowledge_bases: [], is_public: false, usage_count: 0, rating: 5.0 };
    addAgent(agent);
    selectAgent(agent.id);
    setActiveTab('execute');
  };

  const createCustom = () => {
    const agent = { id: Date.now().toString(), ...newAgent, type: 'custom', tools: [], knowledge_bases: [], is_public: false, usage_count: 0, rating: 5.0 };
    addAgent(agent);
    setNewAgent({ name: '', description: '', system_prompt: '', model_id: 'gpt-4o' });
    setActiveTab('browse');
  };

  const executeAgent = async () => {
    if (!selectedAgent || !executeInput.trim()) return;
    setIsExecuting(true);
    setTimeout(() => {
      setExecuteResult(`**Agent Response:**\n\nI have processed your request: "${executeInput}".\n\nHere is the detailed analysis and solution based on my specialized knowledge.`);
      setIsExecuting(false);
    }, 1500);
  };

  return (
    <div className="h-full flex">
      <div className="w-64 bg-gray-900 border-r border-gray-800 p-4 space-y-2">
        <button onClick={() => setActiveTab('browse')} className={`w-full flex items-center space-x-2 px-3 py-2 rounded-lg ${activeTab === 'browse' ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:bg-gray-800'}`}>
          <Bot className="w-4 h-4" /><span>Browse Agents</span>
        </button>
        <button onClick={() => setActiveTab('create')} className={`w-full flex items-center space-x-2 px-3 py-2 rounded-lg ${activeTab === 'create' ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:bg-gray-800'}`}>
          <Plus className="w-4 h-4" /><span>Create Agent</span>
        </button>
        {selectedAgent && (
          <button onClick={() => setActiveTab('execute')} className={`w-full flex items-center space-x-2 px-3 py-2 rounded-lg ${activeTab === 'execute' ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:bg-gray-800'}`}>
            <Play className="w-4 h-4" /><span>Execute</span>
          </button>
        )}
      </div>

      <div className="flex-1 p-6 overflow-auto">
        {activeTab === 'browse' && (
          <div>
            <h2 className="text-2xl font-bold mb-2">Pre-built Agents</h2>
            <p className="text-gray-400 mb-6">Choose from our collection of expert AI agents</p>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {TEMPLATES.map((t) => (
                <div key={t.id} onClick={() => createFromTemplate(t.id)} className="bg-gray-800/50 border border-gray-700 rounded-xl p-5 cursor-pointer hover:border-blue-500/50 transition-colors">
                  <div className={`inline-block px-3 py-1 rounded-full text-xs font-medium mb-3 ${t.color}`}>{t.name}</div>
                  <p className="text-sm text-gray-400 mt-1">{t.desc}</p>
                </div>
              ))}
            </div>
            <h2 className="text-2xl font-bold mt-10 mb-2">My Agents</h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {agents.map((agent) => (
                <div key={agent.id} onClick={() => selectAgent(agent.id)} className={`bg-gray-800/50 border rounded-xl p-5 cursor-pointer transition-colors ${selectedAgent === agent.id ? 'border-blue-500' : 'border-gray-700 hover:border-gray-600'}`}>
                  <h3 className="font-semibold">{agent.name}</h3>
                  <p className="text-sm text-gray-400 mt-1">{agent.description}</p>
                  <div className="flex items-center mt-3 space-x-3 text-xs text-gray-500">
                    <span className="flex items-center"><Star className="w-3 h-3 text-yellow-400 mr-1" />{agent.rating}</span>
                    <span>{agent.usage_count} uses</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'create' && (
          <div className="max-w-2xl">
            <h2 className="text-2xl font-bold mb-6">Create Custom Agent</h2>
            <div className="space-y-4">
              <div><label className="block text-sm font-medium mb-1">Name</label><input value={newAgent.name} onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500" placeholder="My Custom Agent" /></div>
              <div><label className="block text-sm font-medium mb-1">Description</label><input value={newAgent.description} onChange={(e) => setNewAgent({ ...newAgent, description: e.target.value })} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500" placeholder="What does this agent do?" /></div>
              <div><label className="block text-sm font-medium mb-1">System Prompt</label><textarea value={newAgent.system_prompt} onChange={(e) => setNewAgent({ ...newAgent, system_prompt: e.target.value })} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500 h-40" placeholder="You are an expert..." /></div>
              <button onClick={createCustom} className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium">Create Agent</button>
            </div>
          </div>
        )}

        {activeTab === 'execute' && selectedAgent && (
          <div className="max-w-3xl">
            <h2 className="text-2xl font-bold mb-2">{agents.find((a) => a.id === selectedAgent)?.name}</h2>
            <div className="space-y-4">
              <textarea value={executeInput} onChange={(e) => setExecuteInput(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500 h-32" placeholder="Enter your request..." />
              <button onClick={executeAgent} disabled={isExecuting} className="bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-medium">{isExecuting ? 'Executing...' : 'Execute'}</button>
              {executeResult && (
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-400 mb-2">Result</h3>
                  <div className="prose prose-invert max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]}>{executeResult}</ReactMarkdown></div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
