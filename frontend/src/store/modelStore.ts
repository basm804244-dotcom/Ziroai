import { create } from 'zustand';

interface Model {
  id: string;
  name: string;
  provider: string;
  category: string;
  capabilities: string[];
  context_window: number;
  pricing_input: number;
  pricing_output: number;
}

interface ModelState {
  models: Model[];
  selectedModel: string;
  favorites: string[];
  setModels: (models: Model[]) => void;
  selectModel: (id: string) => void;
  toggleFavorite: (id: string) => void;
}

export const useModelStore = create<ModelState>((set, get) => ({
  models: [],
  selectedModel: 'gpt-4o',
  favorites: [],
  setModels: (models) => set({ models }),
  selectModel: (id) => set({ selectedModel: id }),
  toggleFavorite: (id) => set((state) => ({
    favorites: state.favorites.includes(id) ? state.favorites.filter((f) => f !== id) : [...state.favorites, id],
  })),
}));
