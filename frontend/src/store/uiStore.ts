import { create } from 'zustand';

interface UIState {
  sidebarOpen: boolean;
  theme: 'dark' | 'light';
  activeTab: string;
  modal: string | null;
  toast: { message: string; type: 'success' | 'error' | 'info' } | null;
  toggleSidebar: () => void;
  setTheme: (theme: 'dark' | 'light') => void;
  setActiveTab: (tab: string) => void;
  setModal: (modal: string | null) => void;
  showToast: (message: string, type: 'success' | 'error' | 'info') => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  theme: 'dark',
  activeTab: 'chat',
  modal: null,
  toast: null,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setTheme: (theme) => set({ theme }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setModal: (modal) => set({ modal }),
  showToast: (message, type) => set({ toast: { message, type } }),
}));
