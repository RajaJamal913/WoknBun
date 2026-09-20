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
    <div className="bg-surface border border-border rounded-xl overflow-hidden flex flex-col hover:border-accent/50 transition">
      <div className="relative aspect-[4/3] bg-surface2 flex items-center justify-center">
        {item.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
        ) : (
          <span className="text-4xl opacity-30">🍽️</span>
        )}
        {item.badge && (
          <span className="absolute top-2 left-2 badge-flame text-white text-[10px] font-bold px-2 py-1 rounded-full uppercase tracking-wide">
            {BADGE_LABEL[item.badge] || item.badge}
          </span>
        )}
      </div>

      <div className="p-4 flex flex-col gap-2 flex-1">
        <h3 className="font-semibold text-sm md:text-base leading-tight">{item.name}</h3>
        {item.note && <p className="text-xs text-muted leading-snug">{item.note}</p>}

        {hasMultipleSizes && (
          <div className="flex flex-wrap gap-1.5 mt-1">
            {item.prices.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedPriceId(p.id)}
                className={`text-[11px] px-2 py-1 rounded-md border transition ${
                  selectedPriceId === p.id
                    ? "border-accent text-accent bg-accent/10"
                    : "border-border text-muted hover:text-ink"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        )}

        <div className="mt-auto pt-3 flex items-center justify-between">
          <span className="font-bold text-accent2">
            Rs. {selectedPrice ? Number(selectedPrice.price).toLocaleString() : "—"}
          </span>
          <button
            onClick={handleAdd}
            className="bg-accent hover:bg-accent/90 text-white text-xs font-bold px-3 py-2 rounded-full transition"
          >
            Add to Cart
          </button>
        </div>
      </div>
    </div>
  );
}