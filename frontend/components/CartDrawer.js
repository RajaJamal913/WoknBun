"use client";

import { useCart } from "@/context/CartContext";
import Link from "next/link";

export default function CartDrawer() {
  const {
    items,
    updateQuantity,
    removeItem,
    subtotal,
    tax,
    deliveryCharges,
    grandTotal,
    isDrawerOpen,
    setDrawerOpen,
  } = useCart();

  if (!isDrawerOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/60" onClick={() => setDrawerOpen(false)} />
      <div className="relative w-full max-w-sm bg-surface border-l border-border h-full flex flex-col">
        <div className="flex items-center justify-between px-4 py-4 border-b border-border">
          <h2 className="font-display text-lg">Your Cart</h2>
          <button onClick={() => setDrawerOpen(false)} className="text-muted hover:text-ink text-2xl leading-none">
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {items.length === 0 && (
            <p className="text-muted text-sm text-center mt-10">Your cart is empty. Add something tasty!</p>
          )}
          {items.map((item) => (
            <div key={item.key} className="flex items-start justify-between gap-3 border-b border-border pb-4">
              <div className="flex-1">
                <p className="font-semibold text-sm">{item.name}</p>
                {item.sizeLabel && <p className="text-xs text-muted">{item.sizeLabel}</p>}
                <p className="text-accent2 text-sm font-bold mt-1">
                  Rs. {(item.unitPrice * item.quantity).toLocaleString()}
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <button
                    onClick={() => updateQuantity(item.key, -1)}
                    className="w-6 h-6 rounded-full bg-accent text-white flex items-center justify-center text-sm"
                  >
                    −
                  </button>
                  <span className="text-sm w-5 text-center">{item.quantity}</span>
                  <button
                    onClick={() => updateQuantity(item.key, 1)}
                    className="w-6 h-6 rounded-full bg-accent text-white flex items-center justify-center text-sm"
                  >
                    +
                  </button>
                </div>
              </div>
              <button
                onClick={() => removeItem(item.key)}
                aria-label="Remove item"
                className="text-muted hover:text-accent"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6" />
                </svg>
              </button>
            </div>
          ))}
        </div>

        {items.length > 0 && (
          <div className="border-t border-border px-4 py-4 space-y-2">
            <div className="flex justify-between text-sm text-muted">
              <span>Subtotal</span>
              <span>Rs. {subtotal.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-sm text-muted">
              <span>Delivery Charges</span>
              <span>Rs. {deliveryCharges.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-sm text-muted">
              <span>Tax (16%)</span>
              <span>Rs. {tax.toLocaleString()}</span>
            </div>
            <div className="flex justify-between font-bold text-base pt-2 border-t border-border">
              <span>Grand Total</span>
              <span className="text-accent2">Rs. {grandTotal.toLocaleString()}</span>
            </div>
            <Link
              href="/checkout"
              onClick={() => setDrawerOpen(false)}
              className="block text-center bg-accent hover:bg-accent/90 text-white font-bold py-3 rounded-full mt-3 transition"
            >
              Checkout
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}