"use client";

import { useCart } from "@/context/CartContext";

export default function MobileCartBar() {
  const { itemCount, grandTotal, setDrawerOpen } = useCart();

  if (itemCount === 0) return null;

  return (
    <button
      onClick={() => setDrawerOpen(true)}
      className="fixed bottom-4 left-4 right-4 md:hidden z-40 bg-gradient-to-r from-accent to-accent-deep text-white rounded-full px-5 py-3.5 flex items-center justify-between shadow-glow ring-1 ring-white/20 active:scale-[0.98] transition"
    >
      <span className="font-extrabold text-sm">Rs. {grandTotal.toLocaleString()}</span>
      <span className="font-bold text-sm">View Cart ({itemCount}) →</span>
    </button>
  );
}