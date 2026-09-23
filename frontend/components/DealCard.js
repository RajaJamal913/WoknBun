"use client";

import { useCart } from "@/context/CartContext";

export default function DealCard({ deal }) {
  const { addItem } = useCart();
  const lines = deal.description.split("\n").filter(Boolean);

  function handleAdd() {
    addItem({ name: deal.name, sizeLabel: "Deal", unitPrice: parseFloat(deal.price) });
  }

  return (
    <div className="group relative bg-gradient-to-b from-surface2 to-surface border border-border rounded-2xl overflow-hidden flex flex-col h-full hover:border-accent/40 hover:-translate-y-1 hover:shadow-card transition duration-300">
      <div className="relative aspect-[16/10] bg-surface2 flex items-center justify-center overflow-hidden">
        {deal.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={deal.image_url}
            alt={deal.name}
            className="w-full h-full object-cover group-hover:scale-105 transition duration-500"
          />
        ) : (
          <span className="text-3xl opacity-30">🍽️</span>
        )}
        <div className="absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-surface2/80 to-transparent pointer-events-none" />
        {deal.badge && (
          <span className="absolute top-2.5 left-2.5 badge-flame text-black text-[10px] font-extrabold px-2.5 py-1 rounded-full uppercase tracking-wide shadow-md">
            {deal.badge}
          </span>
        )}
      </div>

      <div className="p-4 flex flex-col gap-3 flex-1">
        <h3 className="font-display font-bold text-sm leading-tight">{deal.name}</h3>
        <ul className="text-xs text-muted space-y-1 flex-1">
          {lines.map((line, i) => (
            <li key={i} className="flex gap-1.5">
              <span className="text-accent">•</span>
              <span>{line}</span>
            </li>
          ))}
        </ul>
        <div className="flex items-center justify-between pt-3 border-t border-border">
          <span className="font-display font-extrabold text-gold">Rs. {Number(deal.price).toLocaleString()}</span>
          <button
            onClick={handleAdd}
            className="bg-accent hover:bg-accent-hover text-white text-xs font-bold px-4 py-2 rounded-full shadow-glow active:scale-95 transition"
          >
            + Add
          </button>
        </div>
      </div>
    </div>
  );
}