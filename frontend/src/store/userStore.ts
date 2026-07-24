import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: string;
  plan: string;
  avatar_url?: string;
}

interface UserState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  login: (token: string, user: User) => void;
  logout: () => void;
  checkAuth: () => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      login: (token, user) => {
        localStorage.setItem('access_token', token);
        set({ user, isAuthenticated: true });
      },
      logout: () => {
        localStorage.removeItem('access_token');
        set({ user: null, isAuthenticated: false });
      },
      checkAuth: () => {
        const token = localStorage.getItem('access_token');
        if (!token) {
          set({ isAuthenticated: false, isLoading: false });
          return;
        }
        set({ isAuthenticated: true, isLoading: false });
      },
    }),
    { name: 'user-storage' }
  )
);
