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

function getFallbackOfflineUser(): User {
  return {
    id: -1,
    username: "offline_station",
    email: "offline@local",
    is_active: true,
    roles: [],
  };
}

function parseCachedUser(): User | null {
  const cachedRaw = localStorage.getItem(CACHED_USER_KEY);
  if (!cachedRaw) {
    return null;
  }
  try {
    return JSON.parse(cachedRaw) as User;
  } catch {
    localStorage.removeItem(CACHED_USER_KEY);
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [sessionMode] = useState<SessionMode>("anonymous");
  const [isInitializing, setIsInitializing] = useState(true);

  const clearSession = useCallback(() => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(CACHED_USER_KEY);
    setAccessToken(null);
    setUser(null);
  }, []);

  const handleLogin = useCallback(async (_username: string, _password: string) => {
    // In the 2.0 no-login model we don't support interactive login.
    // This is a no-op to satisfy existing call sites.
    return;
  }, []);

  const handleLogout = useCallback(() => {
    clearSession();
  }, [clearSession]);

  // Immediately mark initialization as complete; we don't perform any
  // background login or token refresh in the no-login 2.0 desktop app.
  useEffect(() => {
    setIsInitializing(false);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token: accessToken,
      isAuthenticated: false,
      canAccessApp: true,
      isOfflineSession: false,
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
