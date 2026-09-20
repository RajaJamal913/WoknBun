"use client";

import { useCart } from "@/context/CartContext";

export default function DealCard({ deal }) {
  const { addItem } = useCart();
  const lines = deal.description.split("\n").filter(Boolean);

  function handleAdd() {
    addItem({ name: deal.name, sizeLabel: "Deal", unitPrice: parseFloat(deal.price) });
  }

  return (
    <div className="bg-gradient-to-b from-surface2 to-surface border border-border rounded-xl overflow-hidden flex flex-col h-full">
      <div className="relative aspect-[16/10] bg-surface2 flex items-center justify-center">
        {deal.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={deal.image_url} alt={deal.name} className="w-full h-full object-cover" />
        ) : (
          <span className="text-3xl opacity-30">🍽️</span>
        )}
      </div>

      <div className="p-4 flex flex-col gap-3 flex-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-display text-sm leading-tight">{deal.name}</h3>
        </div>
        <ul className="text-xs text-muted space-y-1 flex-1">
          {lines.map((line, i) => (
            <li key={i}>• {line}</li>
          ))}
        </ul>
        {deal.badge && (
          <span className="text-[10px] font-semibold text-accent2 uppercase tracking-wide">{deal.badge}</span>
        )}
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <span className="font-bold text-accent2">Rs. {Number(deal.price).toLocaleString()}</span>
          <button
            onClick={handleAdd}
            className="bg-accent hover:bg-accent/90 text-white text-xs font-bold px-3 py-2 rounded-full transition"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  );
}