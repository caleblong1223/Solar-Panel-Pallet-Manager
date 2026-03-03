import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getCurrentUser, login as apiLogin } from "./authApi";
import { getTokenExpiryMs } from "./jwt";
import type { User } from "./types";

const ACCESS_TOKEN_KEY = "pm2_access_token";
const REFRESH_WINDOW_MS = 5 * 60 * 1000;
const SHARED_USERNAME = import.meta.env.VITE_SHARED_USERNAME ?? "critical_e2e_user";
const SHARED_PASSWORD = import.meta.env.VITE_SHARED_PASSWORD ?? "critical-e2e-password";

type AuthContextValue = {
  token: string | null;
  isAuthenticated: boolean;
  isInitializing: boolean;
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(() => localStorage.getItem(ACCESS_TOKEN_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [hasTriedAutoLogin, setHasTriedAutoLogin] = useState(false);

  const clearSession = useCallback(() => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    setAccessToken(null);
    setUser(null);
  }, []);

  const refreshSession = useCallback(async (token: string) => {
    try {
      const profile = await getCurrentUser(token);
      setUser(profile);
      return true;
    } catch {
      clearSession();
      return false;
    }
  }, [clearSession]);

  const handleLogin = useCallback(async (username: string, password: string) => {
    const result = await apiLogin(username, password);
    localStorage.setItem(ACCESS_TOKEN_KEY, result.access_token);
    setAccessToken(result.access_token);
    await refreshSession(result.access_token);
  }, [refreshSession]);

  const handleLogout = useCallback(() => {
    clearSession();
  }, [clearSession]);

  useEffect(() => {
    let cancelled = false;

    const initialize = async () => {
      // If we already have a token, just refresh the session.
      if (accessToken) {
        await refreshSession(accessToken);
        if (!cancelled) {
          setIsInitializing(false);
        }
        return;
      }

      // Otherwise, attempt background login with shared credentials once.
      if (!hasTriedAutoLogin) {
        try {
          const result = await apiLogin(SHARED_USERNAME, SHARED_PASSWORD);
          localStorage.setItem(ACCESS_TOKEN_KEY, result.access_token);
          setAccessToken(result.access_token);
          await refreshSession(result.access_token);
        } catch {
          // If auto login fails, leave user unauthenticated.
        } finally {
          if (!cancelled) {
            setHasTriedAutoLogin(true);
            setIsInitializing(false);
          }
        }
        return;
      }

      if (!cancelled) {
        setIsInitializing(false);
      }
    };

    void initialize();

    return () => {
      cancelled = true;
    };
  }, [accessToken, hasTriedAutoLogin, refreshSession]);

  useEffect(() => {
    if (!accessToken) {
      return;
    }

    const interval = window.setInterval(() => {
      const expiryMs = getTokenExpiryMs(accessToken);
      if (!expiryMs) {
        return;
      }

      const msUntilExpiry = expiryMs - Date.now();
      if (msUntilExpiry <= 0) {
        clearSession();
        return;
      }

      if (msUntilExpiry <= REFRESH_WINDOW_MS) {
        void refreshSession(accessToken);
      }
    }, 60_000);

    return () => window.clearInterval(interval);
  }, [accessToken, clearSession, refreshSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token: accessToken,
      isAuthenticated: Boolean(accessToken && user),
      isInitializing,
      user,
      login: handleLogin,
      logout: handleLogout,
    }),
    [accessToken, user, isInitializing, handleLogin, handleLogout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
