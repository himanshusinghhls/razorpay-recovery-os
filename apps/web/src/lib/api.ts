import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from "axios";

export const API_BASE = `${
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
}/api/v1`;

/**
 * The access token lives in a module variable, never in localStorage or a
 * readable cookie.
 *
 * An XSS payload can read anything in web storage, and a token parked there
 * outlives the page. Holding it in memory means it dies with the tab, and the
 * only durable credential is the httpOnly refresh cookie that script cannot
 * touch.
 */
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
  // Required so the browser sends the httpOnly refresh cookie.
  withCredentials: true,
  timeout: 30_000,
});

/**
 * Endpoints that fan out to the model or grind through a large batch, and so
 * legitimately outrun the default timeout.
 */
export const SLOW_REQUEST = { timeout: 120_000 } as const;

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.set("Authorization", `Bearer ${accessToken}`);
  }
  return config;
});

/**
 * Single-flight refresh.
 *
 * When a burst of parallel requests all 401 at once, every one of them would
 * otherwise fire its own /auth/refresh. Because refresh tokens rotate and
 * re-use is treated as theft, that would revoke the family and log the user
 * out. Instead the first failure starts one refresh and the rest await it.
 */
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
        // The refresh cookie is gone, expired, or was revoked — the session is
        // genuinely over, so hand control back to the auth provider.
        setAccessToken(null);
        onSessionLost?.();
      }
    }

    return Promise.reject(error);
  },
);

/** Pull a human-readable message out of a FastAPI error response. */
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
