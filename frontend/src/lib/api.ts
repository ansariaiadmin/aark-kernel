/**
 * Single place that knows how the browser reaches the API.
 *
 * Why this exists
 * ---------------
 * `page.tsx` used to call `fetch('/api/v1/...')` with *relative* URLs while the
 * backend lives on a different origin (:8000) — so every one of those calls hit
 * the Next.js server and 404'd. The WebSocket meanwhile was hardcoded to
 * `ws://localhost:8000`, which only works when the browser runs on the same
 * machine as the API (never true in Docker-on-a-server, never true behind a
 * preview proxy).
 *
 * Rules enforced here:
 *  - REST goes same-origin (`/api/v1/...`) and is proxied by `next.config.mjs`
 *    rewrites to the backend. No CORS, no hardcoded host in browser code.
 *  - `NEXT_PUBLIC_API_URL` may still override the base for split deployments;
 *    when it is relative or empty we stay same-origin.
 *  - WebSocket URL is derived from the effective API base and upgrades
 *    ws->wss automatically on https pages.
 */

const RAW_API_URL = (process.env.NEXT_PUBLIC_API_URL || '').trim().replace(/\/+$/, '');
const RAW_WS_URL = (process.env.NEXT_PUBLIC_WS_URL || '').trim().replace(/\/+$/, '');

/** REST base. Empty string === same-origin (proxied by Next). */
export const API_BASE: string = RAW_API_URL;

/** `true` when REST calls go to a different origin than the page. */
export const IS_CROSS_ORIGIN: boolean = /^https?:\/\//i.test(API_BASE);

/** Build a REST URL for an absolute API path such as `/api/v1/health/live`. */
export function apiUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  // API_BASE already ends with /api/v1 in split deployments; avoid doubling it.
  if (API_BASE && normalized.startsWith('/api/v1/')) {
    return `${API_BASE}${normalized.slice('/api/v1'.length)}`;
  }
  return `${API_BASE}${normalized}`;
}

/** Build a WebSocket URL for an absolute WS path such as `/api/v1/ws/ws`. */
export function wsUrl(path: string, params?: Record<string, string | undefined>): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  let base = RAW_WS_URL;

  if (!base) {
    if (typeof window !== 'undefined' && window.location?.host) {
      const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // Same-origin by default: works behind any reverse proxy that upgrades
      // /api/v1/ws/* to the backend.
      base = `${scheme}//${window.location.host}`;
    } else if (API_BASE) {
      base = API_BASE.replace(/^http/i, 'ws');
    }
  }

  if (!base) return normalized;

  const trimmed = base.replace(/\/+$/, '');
  const suffix = normalized.startsWith('/api/v1/') && /^wss?:\/\//i.test(trimmed) && /\/api\/v1$/.test(trimmed)
    ? normalized.slice('/api/v1'.length)
    : normalized;

  const qs = params
    ? Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
        .join('&')
    : '';

  return qs ? `${trimmed}${suffix}?${qs}` : `${trimmed}${suffix}`;
}
