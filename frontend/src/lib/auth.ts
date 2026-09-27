'use client';

/**
 * JWT handling for the browser.
 *
 * The dashboard read `localStorage.getItem('aark_token')` to open its WebSocket
 * but *nothing in the app ever wrote that key* — so the socket never connected
 * and every real-time panel (market ticker, orders, positions, risk alerts)
 * stayed permanently empty. This module owns the token lifecycle so there is
 * exactly one reader/writer.
 */

import { apiUrl } from './api';

const TOKEN_KEY = 'aark_token';
const USER_KEY = 'aark_user';

export interface SessionUser {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_superuser: boolean;
}

function storage(): Storage | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage;
  } catch {
    return null; // private mode / disabled storage
  }
}

export function getToken(): string | null {
  return storage()?.getItem(TOKEN_KEY) ?? null;
}

export function setToken(token: string): void {
  storage()?.setItem(TOKEN_KEY, token);
}

export function getUser(): SessionUser | null {
  const raw = storage()?.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as SessionUser;
  } catch {
    return null;
  }
}

export function setUser(user: SessionUser | null): void {
  const s = storage();
  if (!s) return;
  if (user) s.setItem(USER_KEY, JSON.stringify(user));
  else s.removeItem(USER_KEY);
}

export function clearSession(): void {
  const s = storage();
  s?.removeItem(TOKEN_KEY);
  s?.removeItem(USER_KEY);
}

export function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getToken();
  const headers = new Headers(extra);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return headers;
}

/** `fetch` that injects the Bearer token. Drop-in replacement for `fetch`. */
export function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(apiUrl(path), { ...init, headers: authHeaders(init.headers) });
}

/** POST /auth/login (OAuth2 form) and persist the returned JWT + profile. */
export async function login(email: string, password: string): Promise<SessionUser> {
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch(apiUrl('/api/v1/auth/login'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!res.ok) {
    let detail = 'ورود ناموفق بود';
    try {
      detail = (await res.json())?.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  const data = (await res.json()) as { access_token: string };
  setToken(data.access_token);

  const meRes = await authFetch('/api/v1/auth/me');
  if (!meRes.ok) throw new Error('دریافت پروفایل کاربر ناموفق بود');
  const user = (await meRes.json()) as SessionUser;
  setUser(user);
  return user;
}

export async function logout(): Promise<void> {
  clearSession();
}
