"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import {
  api,
  errorMessage,
  setAccessToken,
  setSessionLostHandler,
} from "./api";

export type Role = "viewer" | "analyst" | "admin";

export interface UserProfile {
  user_id: string;
  email: string;
  full_name: string;
  role: Role;
  merchant_id: string;
  merchant_name: string;
}

interface SessionResponse {
  access_token: string;
  expires_in: number;
  user: UserProfile;
}

interface AuthState {
  user: UserProfile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  can: (minimum: Role) => boolean;
}

const RANK: Record<Role, number> = { viewer: 0, analyst: 1, admin: 2 };

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = useCallback(() => {
    if (refreshTimer.current) {
      clearTimeout(refreshTimer.current);
      refreshTimer.current = null;
    }
  }, []);

  const scheduleRefresh = useCallback(
    function doSchedule(expiresIn: number) {
      clearTimer();
      const leadTime = Math.max(expiresIn - 60, 30) * 1000;
      refreshTimer.current = setTimeout(async () => {
        try {
          const res = await api.post<SessionResponse>("/auth/refresh");
          setAccessToken(res.data.access_token);
          setUser(res.data.user);
          doSchedule(res.data.expires_in);
        } catch {
          setAccessToken(null);
          setUser(null);
        }
      }, leadTime);
    },
    [clearTimer],
  );

  const applySession = useCallback(
    (data: SessionResponse) => {
      setAccessToken(data.access_token);
      setUser(data.user);
      scheduleRefresh(data.expires_in);
    },
    [scheduleRefresh],
  );

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const res = await api.post<SessionResponse>("/auth/refresh");
        if (!cancelled) applySession(res.data);
      } catch {
        if (!cancelled) setAccessToken(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [applySession]);

  useEffect(() => {
    setSessionLostHandler(() => {
      clearTimer();
      setUser(null);
      router.replace("/login");
    });
    return () => setSessionLostHandler(null);
  }, [clearTimer, router]);

  useEffect(() => clearTimer, [clearTimer]);

  const login = useCallback(
    async (email: string, password: string) => {
      try {
        const res = await api.post<SessionResponse>("/auth/login", {
          email,
          password,
        });
        applySession(res.data);
      } catch (err) {
        throw new Error(errorMessage(err, "Unable to sign in"));
      }
    },
    [applySession],
  );

  const logout = useCallback(async () => {
    clearTimer();
    try {
      await api.post("/auth/logout");
    } catch {
      // 
    }
    setAccessToken(null);
    setUser(null);
    router.replace("/login");
  }, [clearTimer, router]);

  const can = useCallback(
    (minimum: Role) => (user ? RANK[user.role] >= RANK[minimum] : false),
    [user],
  );

  const value = useMemo(
    () => ({ user, loading, login, logout, can }),
    [user, loading, login, logout, can],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
