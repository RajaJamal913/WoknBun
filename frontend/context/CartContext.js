"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

const CartContext = createContext(null);
const STORAGE_KEY = "wokandbun_cart_v1";
export const DELIVERY_CHARGES = 250;
export const TAX_RATE = 0.16;

function lineKey(name, sizeLabel) {
  return `${name}__${sizeLabel || "default"}`;
}

export function CartProvider({ children }) {
  const [items, setItems] = useState([]);
  const [isDrawerOpen, setDrawerOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);

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

  function addItem({ name, sizeLabel = "", unitPrice, image = "" }) {
    const key = lineKey(name, sizeLabel);
    setItems((prev) => {
      const existing = prev.find((i) => i.key === key);
      if (existing) {
        return prev.map((i) => (i.key === key ? { ...i, quantity: i.quantity + 1 } : i));
      }
      return [...prev, { key, name, sizeLabel, unitPrice, image, quantity: 1 }];
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
  const tax = useMemo(() => Math.round(subtotal * TAX_RATE * 100) / 100, [subtotal]);
  const deliveryCharges = items.length ? DELIVERY_CHARGES : 0;
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
