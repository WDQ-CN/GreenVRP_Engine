import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  apiKey: string | null;
  isAuthenticated: boolean;
  setApiKey: (key: string) => void;
  clearApiKey: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      apiKey: null,
      isAuthenticated: false,
      setApiKey: (key: string) => {
        localStorage.setItem('greenvrp_api_key', key);
        set({ apiKey: key, isAuthenticated: true });
      },
      clearApiKey: () => {
        localStorage.removeItem('greenvrp_api_key');
        set({ apiKey: null, isAuthenticated: false });
      },
    }),
    {
      name: 'greenvrp-auth',
      partialize: (state) => ({ apiKey: state.apiKey }),
      onRehydrateStorage: () => (state) => {
        if (state?.apiKey) {
          state.isAuthenticated = true;
        }
      },
    }
  )
);
