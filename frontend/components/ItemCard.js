"use client";

import { useState } from "react";
import { useCart } from "@/context/CartContext";

const BADGE_LABEL = {
  best_seller: "Best Seller",
  new: "New",
};

export default function ItemCard({ item }) {
  const { addItem } = useCart();
  const hasMultipleSizes = item.prices.length > 1;
  const [selectedPriceId, setSelectedPriceId] = useState(item.prices[0]?.id);

  const selectedPrice = item.prices.find((p) => p.id === selectedPriceId) || item.prices[0];

  function handleAdd() {
    if (!selectedPrice) return;
    addItem({
      name: item.name,
      sizeLabel: selectedPrice.label,
      unitPrice: parseFloat(selectedPrice.price),
    });
  }

  return (
    <div className="group bg-surface border border-border rounded-2xl overflow-hidden flex flex-col hover:border-accent/40 hover:-translate-y-1 hover:shadow-card transition duration-300">
      <div className="relative aspect-[4/3] bg-surface2 flex items-center justify-center overflow-hidden">
        {item.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.image_url}
            alt={item.name}
            className="w-full h-full object-cover group-hover:scale-105 transition duration-500"
          />
        ) : (
          <span className="text-4xl opacity-30">🍽️</span>
        )}
        <div className="absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-surface/70 to-transparent pointer-events-none" />
        {item.badge && (
          <span className="absolute top-2.5 left-2.5 badge-flame text-black text-[10px] font-extrabold px-2.5 py-1 rounded-full uppercase tracking-wide shadow-md">
            {BADGE_LABEL[item.badge] || item.badge}
          </span>
        )}
      </div>

      <div className="p-4 flex flex-col gap-2 flex-1">
        <h3 className="font-display font-bold text-sm md:text-base leading-tight">{item.name}</h3>
        {item.note && <p className="text-xs text-muted leading-snug">{item.note}</p>}

        {hasMultipleSizes && (
          <div className="flex flex-wrap gap-1.5 mt-1">
            {item.prices.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedPriceId(p.id)}
                className={`text-[11px] px-2.5 py-1 rounded-full border transition ${
                  selectedPriceId === p.id
                    ? "border-accent text-accent bg-accent/15 font-semibold"
                    : "border-border text-muted hover:text-ink hover:border-white/30"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        )}

        <div className="mt-auto pt-3 flex items-center justify-between">
          <span className="font-display font-extrabold text-gold">
            Rs. {selectedPrice ? Number(selectedPrice.price).toLocaleString() : "—"}
          </span>
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