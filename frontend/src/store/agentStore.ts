import { create } from 'zustand';

interface Agent {
  id: string;
  name: string;
  description: string;
  type: string;
  model_id: string;
  tools: string[];
  avatar_url?: string;
  usage_count: number;
  rating: number;
}

interface AgentState {
  agents: Agent[];
  selectedAgent: string | null;
  setAgents: (agents: Agent[]) => void;
  selectAgent: (id: string | null) => void;
  addAgent: (agent: Agent) => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  agents: [],
  selectedAgent: null,
  setAgents: (agents) => set({ agents }),
  selectAgent: (id) => set({ selectedAgent: id }),
  addAgent: (agent) => set((state) => ({ agents: [...state.agents, agent] })),
}));
