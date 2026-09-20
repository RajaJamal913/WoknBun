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

export { API_URL };
