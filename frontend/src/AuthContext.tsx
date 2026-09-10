import { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { login as apiLogin, setToken, getToken } from './api';

/** Identity of the signed-in account, or null when signed out. */
export interface Session {
  username: string;
  role: string;
  displayName: string | null;
}

const SESSION_KEY = 'auth_session';

function storedSession(): Session | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    // Unreadable or unavailable storage just means no remembered identity.
    return null;
  }
}

function rememberSession(session: Session | null) {
  try {
    if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    else localStorage.removeItem(SESSION_KEY);
  } catch {
    // The token is what authorises requests; this is only for display.
  }
}

interface AuthContextValue {
  isLoggedIn: boolean;
  session: Session | null;
  isOwner: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isLoggedIn, setIsLoggedIn] = useState(() => getToken() !== null);
  const [session, setSession] = useState<Session | null>(() =>
    getToken() !== null ? storedSession() : null,
  );

  const login = useCallback(async (username: string, password: string) => {
    const result = await apiLogin(username, password);
    setToken(result.token, result.expires_in);
    const next: Session = {
      username: result.username,
      role: result.role,
      displayName: result.display_name,
    };
    rememberSession(next);
    setSession(next);
    setIsLoggedIn(true);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    rememberSession(null);
    setSession(null);
    setIsLoggedIn(false);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isLoggedIn,
        session,
        // Display only. The server checks the role on every request that needs
        // it; hiding a control is a convenience, never the control itself.
        isOwner: session?.role === 'owner',
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
