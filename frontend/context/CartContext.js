"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getConfig } from "@/lib/api";

const CartContext = createContext(null);
// v2: lines now carry priceId/dealId (the server prices every order from them).
// Old v1 carts have no ids and would be rejected, so they are dropped.
const STORAGE_KEY = "wokandbun_cart_v2";
// Display defaults only - overwritten from /api/config/. The server always
// computes the real totals.
export const DELIVERY_CHARGES = 250;
export const TAX_RATE = 0.16;

function lineKey(name, sizeLabel) {
  return `${name}__${sizeLabel || "default"}`;
}

export function CartProvider({ children }) {
  const [items, setItems] = useState([]);
  const [isDrawerOpen, setDrawerOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [rates, setRates] = useState({ tax: TAX_RATE, delivery: DELIVERY_CHARGES });

  useEffect(() => {
    getConfig()
      .then((c) => setRates({ tax: Number(c.tax_rate), delivery: Number(c.delivery_charges) }))
      .catch(() => {}); // keep the display defaults
  }, []);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) setItems(JSON.parse(raw));
    } catch (e) {
      // ignore corrupt storage
    }
    setHydrated(true);
  }, []);

  // Persist on change
  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch (e) {
      // ignore storage errors (e.g. private mode)
    }
  }, [items, hydrated]);

  function addItem({ name, sizeLabel = "", unitPrice, priceId = null, dealId = null, image = "" }) {
    const key = lineKey(name, sizeLabel);
    setItems((prev) => {
      const existing = prev.find((i) => i.key === key);
      if (existing) {
        return prev.map((i) => (i.key === key ? { ...i, quantity: i.quantity + 1 } : i));
      }
      return [...prev, { key, name, sizeLabel, unitPrice, priceId, dealId, image, quantity: 1 }];
    });
    setDrawerOpen(true);
  }

  function updateQuantity(key, delta) {
    setItems((prev) =>
      prev
        .map((i) => (i.key === key ? { ...i, quantity: i.quantity + delta } : i))
        .filter((i) => i.quantity > 0)
    );
  }

  function removeItem(key) {
    setItems((prev) => prev.filter((i) => i.key !== key));
  }

  function clearCart() {
    setItems([]);
  }

  const subtotal = useMemo(
    () => items.reduce((sum, i) => sum + i.unitPrice * i.quantity, 0),
    [items]
  );
  const tax = useMemo(() => Math.round(subtotal * rates.tax * 100) / 100, [subtotal, rates.tax]);
  const deliveryCharges = items.length ? rates.delivery : 0;
  const grandTotal = subtotal + deliveryCharges + tax;
  const itemCount = items.reduce((sum, i) => sum + i.quantity, 0);

  const value = {
    items,
    addItem,
    updateQuantity,
    removeItem,
    clearCart,
    subtotal,
    tax,
    deliveryCharges,
    grandTotal,
    itemCount,
    taxRate: rates.tax,
    isDrawerOpen,
    setDrawerOpen,
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within a CartProvider");
  return ctx;
}