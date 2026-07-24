'use client';

import { useState, useRef, useEffect } from 'react';
import { useChatStore, useModelStore } from '@/store';
import { Send, Paperclip, Bot, User, Loader2, Copy, Check, RefreshCw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function ChatPanel() {
  const { conversations, activeConversation, addConversation, setActiveConversation, addMessage, updateMessage, isGenerating, setIsGenerating } = useChatStore();
  const { models, selectedModel, selectModel } = useModelStore();
  const [input, setInput] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeConv = conversations.find((c) => c.id === activeConversation);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeConv?.messages]);

  const handleSend = async () => {
    if (!input.trim() || isGenerating) return;
    let convId = activeConversation;
    if (!convId) {
      const newConv = { id: Date.now().toString(), title: input.slice(0, 50), model_id: selectedModel, messages: [], created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
      addConversation(newConv);
      convId = newConv.id;
    }
    const userMsg = { id: Date.now().toString(), role: 'user' as const, content: input, created_at: new Date().toISOString() };
    addMessage(convId, userMsg);
    setInput('');
    setIsGenerating(true);
    const assistantMsgId = (Date.now() + 1).toString();
    addMessage(convId, { id: assistantMsgId, role: 'assistant', content: '', model: selectedModel, created_at: new Date().toISOString() });

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/chat/conversations/${convId}/generate/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token') || ''}` },
      });
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';
      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                fullContent += parsed.content;
                updateMessage(convId, assistantMsgId, fullContent);
              }
            } catch {}
          }
        }
      }
    } catch (error) {
      updateMessage(convId, assistantMsgId, 'Sorry, an error occurred while generating the response.');
    } finally {
      setIsGenerating(false);
    }
  };

  const copyToClipboard = (content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex h-full">
      <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <button onClick={() => setActiveConversation(null)} className="w-full bg-blue-500 hover:bg-blue-600 text-white py-2 rounded-lg font-medium transition-colors">New Chat</button>
        </div>
        <div className="flex-1 overflow-auto p-2 space-y-1">
          {conversations.map((conv) => (
            <button key={conv.id} onClick={() => setActiveConversation(conv.id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate transition-colors ${conv.id === activeConversation ? 'bg-blue-500/20 text-blue-400' : 'hover:bg-gray-800 text-gray-300'}`}>
              {conv.title}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        <div className="h-14 border-b border-gray-800 flex items-center px-6 space-x-4">
          <select value={selectedModel} onChange={(e) => selectModel(e.target.value)} className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500">
            {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
          <span className="text-xs text-gray-500">{models.find((m) => m.id === selectedModel)?.provider}</span>
        </div>

        <div className="flex-1 overflow-auto p-6 space-y-6">
          {!activeConv?.messages.length ? (
            <div className="h-full flex items-center justify-center text-gray-500">
              <div className="text-center">
                <Bot className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                <p className="text-lg">Start a conversation</p>
                <p className="text-sm mt-2">Ask anything to {models.find((m) => m.id === selectedModel)?.name}</p>
              </div>
            </div>
          ) : (
            activeConv.messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-3xl rounded-2xl px-5 py-3 ${msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-800 border border-gray-700'}`}>
                  <div className="flex items-center space-x-2 mb-2">
                    {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4 text-blue-400" />}
                    <span className="text-xs opacity-70">{msg.role === 'assistant' && msg.model ? msg.model : 'You'}</span>
                  </div>
                  <div className="prose prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                  </div>
                  {msg.role === 'assistant' && (
                    <div className="flex items-center space-x-2 mt-3 pt-2 border-t border-gray-700">
                      <button onClick={() => copyToClipboard(msg.content, msg.id)} className="text-gray-400 hover:text-white transition-colors">
                        {copiedId === msg.id ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      </button>
                      <button className="text-gray-400 hover:text-white transition-colors"><RefreshCw className="w-4 h-4" /></button>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t border-gray-800">
          <div className="flex items-end space-x-3 bg-gray-800 border border-gray-700 rounded-xl p-3">
            <button className="text-gray-400 hover:text-white p-1"><Paperclip className="w-5 h-5" /></button>
            <textarea value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder="Message AetherAI..." className="flex-1 bg-transparent resize-none outline-none text-white placeholder-gray-500 max-h-32" rows={1} />
            <button onClick={handleSend} disabled={!input.trim() || isGenerating} className="bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white p-2 rounded-lg transition-colors">
              {isGenerating ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
