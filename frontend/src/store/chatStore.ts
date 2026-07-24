import { create } from 'zustand';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  model?: string;
  metadata?: any;
  created_at: string;
}

interface Conversation {
  id: string;
  title: string;
  model_id: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
}

interface ChatState {
  conversations: Conversation[];
  activeConversation: string | null;
  isGenerating: boolean;
  addConversation: (conv: Conversation) => void;
  setActiveConversation: (id: string | null) => void;
  addMessage: (convId: string, message: Message) => void;
  updateMessage: (convId: string, msgId: string, content: string) => void;
  setIsGenerating: (value: boolean) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  activeConversation: null,
  isGenerating: false,
  addConversation: (conv) => set((state) => ({ conversations: [conv, ...state.conversations], activeConversation: conv.id })),
  setActiveConversation: (id) => set({ activeConversation: id }),
  addMessage: (convId, message) => set((state) => ({
    conversations: state.conversations.map((c) =>
      c.id === convId ? { ...c, messages: [...c.messages, message], updated_at: new Date().toISOString() } : c
    ),
  })),
  updateMessage: (convId, msgId, content) => set((state) => ({
    conversations: state.conversations.map((c) =>
      c.id === convId ? { ...c, messages: c.messages.map((m) => (m.id === msgId ? { ...m, content } : m)) } : c
    ),
  })),
  setIsGenerating: (value) => set({ isGenerating: value }),
}));
