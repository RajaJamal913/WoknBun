// The signed-in customer's session: login tokens + profile, kept in localStorage.
// No React in here, so it can be used from anywhere (and tested on its own).
//
// Access tokens are short-lived; this file quietly swaps them for fresh ones using
// the long-lived refresh token, so customers don't have to sign in again and again.
// If the server says the session is no longer valid (password changed, login removed
// by staff), the session is cleared and the customer is simply treated as signed out.

const KEY = "wokandbun_session_v2";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const REFRESH_BEFORE_MS = 60 * 1000; // renew when less than a minute is left

let cache; // undefined = not read from storage yet
const listeners = new Set();

function store() {
  try {
    return typeof window !== "undefined" ? window.localStorage : null;
  } catch (e) {
    return null;
  }
}

function notify() {
  listeners.forEach((fn) => fn(cache || null));
}

export function getSession() {
  if (cache === undefined) {
    cache = null;
    try {
      const raw = store()?.getItem(KEY);
      if (raw) {
        const s = JSON.parse(raw);
        if (s && s.tokens && s.tokens.access && s.tokens.refresh && s.customer) cache = s;
      }
    } catch (e) {
      // corrupt storage: behave as signed out
    }
  }
  return cache;
}

export function setSession(session) {
  cache = session;
  try {
    store()?.setItem(KEY, JSON.stringify(session));
  } catch (e) {
    // private mode etc.: the session just won't survive a reload
  }
  notify();
}

export function clearSession() {
  cache = null;
  try {
    store()?.removeItem(KEY);
  } catch (e) {
    // ignore
  }
  notify();
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

// Signing in on another tab (or out) updates this one too.
if (typeof window !== "undefined") {
  window.addEventListener("storage", (e) => {
    if (e.key === KEY || e.key === null) {
      cache = undefined;
      getSession();
      notify();
    }
  });
}

function tokenExpiryMs(token) {
  try {
    const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(payload)).exp * 1000;
  } catch (e) {
    return 0; // unreadable = treat as already expired
  }
}

let refreshing = null;

async function refreshTokens() {
  const s = getSession();
  if (!s) return null;
  try {
    const res = await fetch(`${API_URL}/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: s.tokens.refresh }),
    });
    if (res.status === 401) {
      clearSession(); // really over: expired, or the password changed / staff removed the login
      return null;
    }
    if (!res.ok) return null; // server hiccup: keep the session and try again later
    const tokens = await res.json();
    const current = getSession();
    if (!current) return null;
    setSession({ ...current, tokens });
    return tokens.access;
  } catch (e) {
    return null; // offline
  }
}

function refreshOnce() {
  refreshing = refreshing || refreshTokens().finally(() => { refreshing = null; });
  return refreshing;
}

// A usable access token, or null when signed out. Renews it first if it is about to expire.
export async function freshAccessToken() {
  const s = getSession();
  if (!s) return null;
  if (tokenExpiryMs(s.tokens.access) - Date.now() > REFRESH_BEFORE_MS) return s.tokens.access;
  return refreshOnce();
}

// fetch() for signed-in-only endpoints. Retries once with a new token if the server rejects the old one.
export async function authFetch(path, options = {}) {
  const call = (token) =>
    fetch(`${API_URL}${path}`, {
      ...options,
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...(options.headers || {}), Authorization: `Bearer ${token}` },
    });

  let token = await freshAccessToken();
  if (!token) throw new Error("Please sign in again.");
  let res = await call(token);
  if (res.status === 401) {
    token = await refreshOnce();
    if (!token) throw new Error("Please sign in again.");
    res = await call(token);
    if (res.status === 401) {
      clearSession();
      throw new Error("Please sign in again.");
    }
  }
  return res;
}