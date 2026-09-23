const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

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
    throw new Error(err.detail || "Could not place order. Please check your details and try again.");
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
    const firstFieldError = Object.values(data).flat()[0];
    throw new Error(data.detail || firstFieldError || "Something went wrong. Please try again.");
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