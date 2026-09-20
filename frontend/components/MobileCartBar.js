"use client";

import { useCart } from "@/context/CartContext";

export default function MobileCartBar() {
  const { itemCount, grandTotal, setDrawerOpen } = useCart();

  if (itemCount === 0) return null;

  return (
    <button
      onClick={() => setDrawerOpen(true)}
      className="fixed bottom-4 left-4 right-4 md:hidden z-40 bg-accent text-white rounded-full px-5 py-3 flex items-center justify-between shadow-lg shadow-black/40"
    >
      <span className="font-bold text-sm">Rs. {grandTotal.toLocaleString()}</span>
      <span className="font-bold text-sm">View Cart ({itemCount}) →</span>
    </button>
  );
}
