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
  const res = await fetch(`${API_URL}/orders/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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

export function registerCustomer(payload) {
  return postJSON("/auth/register/", payload);
}

export function loginCustomer(email) {
  return postJSON("/auth/login/", { email });
}

export { API_URL };