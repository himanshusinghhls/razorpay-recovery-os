import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from "axios";

export const API_BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
  }/api/v1`;

let accessToken: string | null = null;
let onSessionLost: (() => void) | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export function setSessionLostHandler(handler: (() => void) | null) {
  onSessionLost = handler;
}

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  timeout: 30_000,
});

export const SLOW_REQUEST = { timeout: 120_000 } as const;

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.set("Authorization", `Bearer ${accessToken}`);
  }
  return config;
});

let refreshInFlight: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  if (!refreshInFlight) {
    refreshInFlight = axios
      .post<{ access_token: string }>(
        `${API_BASE}/auth/refresh`,
        {},
        { withCredentials: true },
      )
      .then((res) => {
        const token = res.data.access_token;
        setAccessToken(token);
        return token;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined;

    const isAuthCall =
      original?.url?.includes("/auth/refresh") ||
      original?.url?.includes("/auth/login");

    if (
      error.response?.status === 401 &&
      original &&
      !original._retried &&
      !isAuthCall
    ) {
      original._retried = true;
      try {
        const token = await refreshAccessToken();
        original.headers.set("Authorization", `Bearer ${token}`);
        return api(original);
      } catch {
        setAccessToken(null);
        onSessionLost?.();
      }
    }

    return Promise.reject(error);
  },
);

export function errorMessage(err: unknown, fallback = "Something went wrong") {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.message) return detail[0].message;
    if (err.code === "ECONNABORTED") return "Request timed out";
    if (!err.response) return "Cannot reach the API server";
  }
  return fallback;
}
