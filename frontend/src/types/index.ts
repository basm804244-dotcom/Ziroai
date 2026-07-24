export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: string;
  plan: string;
  avatar_url?: string;
  mfa_enabled: boolean;
  created_at: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  attachments?: any[];
  metadata?: any;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  model_id: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
}

export interface Model {
  id: string;
  name: string;
  provider: string;
  category: string;
  capabilities: string[];
  context_window: number;
  pricing_input: number;
  pricing_output: number;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  type: string;
  model_id: string;
  system_prompt: string;
  tools: string[];
  knowledge_bases: string[];
  is_public: boolean;
  usage_count: number;
  rating: number;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  project_id: string;
  document_count: number;
  chunk_count: number;
  status: string;
}
