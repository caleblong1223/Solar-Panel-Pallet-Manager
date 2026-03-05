import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getCurrentUser, login as apiLogin } from "./authApi";
import { getTokenExpiryMs } from "./jwt";
import type { User } from "./types";

const ACCESS_TOKEN_KEY = "pm2_access_token";
const CACHED_USER_KEY = "pm2_cached_user";
const REFRESH_WINDOW_MS = 5 * 60 * 1000;
const SHARED_USERNAME = import.meta.env.VITE_SHARED_USERNAME ?? "critical_e2e_user";
const SHARED_PASSWORD = import.meta.env.VITE_SHARED_PASSWORD ?? "critical-e2e-password";
type SessionMode = "anonymous" | "authenticated" | "offline";

type AuthContextValue = {
  token: string | null;
  isAuthenticated: boolean;
  canAccessApp: boolean;
  isOfflineSession: boolean;
  isInitializing: boolean;
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(() => localStorage.getItem(ACCESS_TOKEN_KEY));
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem(CACHED_USER_KEY);
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw) as User;
    } catch {
      return null;
    }
  });
  const [sessionMode, setSessionMode] = useState<SessionMode>("anonymous");
  const [isInitializing, setIsInitializing] = useState(true);
  const [hasTriedAutoLogin, setHasTriedAutoLogin] = useState(false);

  const clearSession = useCallback(() => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(CACHED_USER_KEY);
    setAccessToken(null);
    setUser(null);
    setSessionMode("anonymous");
  }, []);

  const refreshSession = useCallback(async (token: string) => {
    try {
      const profile = await getCurrentUser(token);
      setUser(profile);
      localStorage.setItem(CACHED_USER_KEY, JSON.stringify(profile));
      setSessionMode("authenticated");
      return true;
    } catch {
      return false;
    }
  }, []);

  const handleLogin = useCallback(async (username: string, password: string) => {
    const result = await apiLogin(username, password);
    localStorage.setItem(ACCESS_TOKEN_KEY, result.access_token);
    setAccessToken(result.access_token);
    const didRefresh = await refreshSession(result.access_token);
    if (!didRefresh) {
      throw new Error("Unable to load session profile");
    }
  }, [refreshSession]);

  const handleLogout = useCallback(() => {
    clearSession();
  }, [clearSession]);

  useEffect(() => {
    let cancelled = false;

    const initialize = async () => {
      if (accessToken) {
        const didRefresh = await refreshSession(accessToken);
        if (!didRefresh) {
          setAccessToken(null);
          localStorage.removeItem(ACCESS_TOKEN_KEY);
          const cachedRaw = localStorage.getItem(CACHED_USER_KEY);
          if (cachedRaw) {
            try {
              setUser(JSON.parse(cachedRaw) as User);
              setSessionMode("offline");
            } catch {
              localStorage.removeItem(CACHED_USER_KEY);
              setUser(null);
              setSessionMode("anonymous");
            }
          } else {
            setSessionMode("anonymous");
          }
        }
        if (!cancelled) {
          setIsInitializing(false);
        }
        return;
      }

      if (!hasTriedAutoLogin) {
        try {
          const result = await apiLogin(SHARED_USERNAME, SHARED_PASSWORD);
          localStorage.setItem(ACCESS_TOKEN_KEY, result.access_token);
          setAccessToken(result.access_token);
          await refreshSession(result.access_token);
        } catch {
          const cachedRaw = localStorage.getItem(CACHED_USER_KEY);
          if (cachedRaw) {
            try {
              setUser(JSON.parse(cachedRaw) as User);
              setSessionMode("offline");
            } catch {
              localStorage.removeItem(CACHED_USER_KEY);
              setUser(null);
              setSessionMode("anonymous");
            }
          } else {
            setSessionMode("anonymous");
          }
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
      isAuthenticated: sessionMode === "authenticated",
      // Do not block app shell access on auth bootstrap failures.
      // Individual API calls can still surface connection/auth errors.
      canAccessApp: true,
      isOfflineSession: sessionMode === "offline",
      isInitializing,
      user,
      login: handleLogin,
      logout: handleLogout,
    }),
    [accessToken, sessionMode, user, isInitializing, handleLogin, handleLogout]
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
