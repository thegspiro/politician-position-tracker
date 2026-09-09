import { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { login as apiLogin, setToken, getToken } from './api';

interface AuthContextValue {
  isLoggedIn: boolean;
  login: (password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isLoggedIn, setIsLoggedIn] = useState(() => getToken() !== null);

  const login = useCallback(async (password: string) => {
    const { token, expires_in } = await apiLogin(password);
    setToken(token, expires_in);
    setIsLoggedIn(true);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setIsLoggedIn(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isLoggedIn, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
