import { authFetch, clearSession, freshAccessToken, getSession, setSession } from "./session";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// DRF returns {"detail": "..."} or nested field errors like
// {"items": [{"price_id": ["..."]}]} - dig out the first human-readable string.
function firstErrorMessage(data) {
  if (!data) return "";
  if (typeof data === "string") return data;
  if (Array.isArray(data)) {
    for (const v of data) {
      const m = firstErrorMessage(v);
      if (m) return m;
    }
    return "";
  }
  if (typeof data === "object") {
    if (data.detail) return firstErrorMessage(data.detail);
    for (const v of Object.values(data)) {
      const m = firstErrorMessage(v);
      if (m) return m;
    }
  }
  return "";
}

async function get(path) {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch ${path}`);
  return res.json();
}

export function getCategories() {
  return get("/categories/");
}

export function getMenuItems() {
  return get("/menu-items/");
}

export function getConfig() {
  return get("/config/");
}

export function getDeals() {
  return get("/deals/");
}

export async function createOrder(payload) {
  // Signed in? Send the token so the order lands in "My account". No token (or an expired one)
  // simply means the order is placed as a guest - it must never block checkout.
  const token = await freshAccessToken();
  const res = await fetch(`${API_URL}/orders/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(firstErrorMessage(err) || "Could not place order. Please check your details and try again.");
  }
  return res.json();
}

async function postJSON(path, payload) {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    // Field errors come back like {"email": ["..."]}; pull the first message out.
    throw new Error(firstErrorMessage(data) || "Something went wrong. Please try again.");
  }
  return data;
}

// ---- Customer accounts -------------------------------------------------------

async function accountPost(path, payload, fallback) {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(firstErrorMessage(data) || fallback);
  return data;
}

async function accountJson(res, fallback) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(firstErrorMessage(data) || fallback);
  return data;
}

export async function registerCustomer(details) {
  const body = await accountPost("/auth/register/", details, "Could not create your account. Please try again.");
  setSession(body); // { tokens, customer }
  return body.customer;
}

export async function loginCustomer(identifier, password) {
  const body = await accountPost("/auth/login/", { identifier, password }, "Could not sign you in. Please try again.");
  setSession(body);
  return body.customer;
}

export function logoutCustomer() {
  clearSession();
}

export async function getMyOrders() {
  return accountJson(await authFetch("/auth/orders/"), "Could not load your orders.");
}

export async function updateMyProfile(details) {
  const customer = await accountJson(
    await authFetch("/auth/me/", { method: "PATCH", body: JSON.stringify(details) }),
    "Could not save your details."
  );
  const s = getSession();
  if (s) setSession({ ...s, customer });
  return customer;
}

export async function changeMyPassword(currentPassword, newPassword) {
  const body = await accountJson(
    await authFetch("/auth/change-password/", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),
    "Could not change your password."
  );
  const s = getSession();
  if (s) setSession({ ...s, tokens: body.tokens }); // the old tokens stopped working; these are the new ones
  return body.customer;
}

export { API_URL };