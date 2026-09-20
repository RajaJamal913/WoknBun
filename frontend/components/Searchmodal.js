"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useSearch } from "@/context/SearchContext";
import { useCart } from "@/context/CartContext";
import { getMenuItems, getDeals } from "@/lib/api";

export default function SearchModal() {
  const { searchOpen, setSearchOpen } = useSearch();
  const { addItem } = useCart();
  const router = useRouter();
  const pathname = usePathname();

  const [query, setQuery] = useState("");
  const [items, setItems] = useState([]);
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const loadedRef = useRef(false);
  const inputRef = useRef(null);

  // Fetch the searchable data once, the first time the modal is opened.
  useEffect(() => {
    if (!searchOpen || loadedRef.current) return;
    loadedRef.current = true;
    setLoading(true);
    Promise.all([getMenuItems(), getDeals()])
      .then(([itemData, dealData]) => {
        setItems(itemData);
        setDeals(dealData);
      })
      .catch(() => setLoadError("Couldn't load the menu. Please try again."))
      .finally(() => setLoading(false));
  }, [searchOpen]);

  useEffect(() => {
    if (searchOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
    }
  }, [searchOpen]);

  const matchedItems = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return items.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        (item.description && item.description.toLowerCase().includes(q)) ||
        (item.category && item.category.toLowerCase().includes(q))
    );
  }, [items, query]);

  const matchedDeals = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return deals.filter(
      (deal) =>
        deal.name.toLowerCase().includes(q) ||
        (deal.description && deal.description.toLowerCase().includes(q))
    );
  }, [deals, query]);

  const hasQuery = query.trim().length > 0;
  const hasResults = matchedItems.length > 0 || matchedDeals.length > 0;

  function goToCategory(slug) {
    setSearchOpen(false);
    if (pathname === "/") {
      const el = document.getElementById(slug);
      if (el) {
        const y = el.getBoundingClientRect().top + window.scrollY - 116;
        window.scrollTo({ top: y, behavior: "smooth" });
      }
    } else {
      router.push(`/#${slug}`);
    }
  }

  function quickAddItem(item) {
    const price = item.prices?.[0];
    if (!price) return;
    addItem({ name: item.name, sizeLabel: price.label, unitPrice: parseFloat(price.price) });
    setSearchOpen(false);
  }

  function quickAddDeal(deal) {
    addItem({ name: deal.name, sizeLabel: "Deal", unitPrice: parseFloat(deal.price) });
    setSearchOpen(false);
  }

  if (!searchOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center pt-16 md:pt-24 px-4">
      <div className="absolute inset-0 bg-black/80" onClick={() => setSearchOpen(false)} />
      <div className="relative w-full max-w-xl bg-surface border border-border rounded-2xl overflow-hidden max-h-[75vh] flex flex-col">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-muted shrink-0">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search burgers, pizza, tenders, deals…"
            className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted"
          />
          <button
            onClick={() => setSearchOpen(false)}
            className="text-muted hover:text-ink text-xl leading-none shrink-0"
            aria-label="Close search"
          >
            ×
          </button>
        </div>

        <div className="overflow-y-auto flex-1">
          {loading && <p className="text-center text-muted text-sm py-10">Loading menu…</p>}
          {loadError && <p className="text-center text-red-400 text-sm py-10">{loadError}</p>}

          {!loading && !loadError && !hasQuery && (
            <p className="text-center text-muted text-sm py-10">Start typing to search the menu.</p>
          )}

          {!loading && !loadError && hasQuery && !hasResults && (
            <p className="text-center text-muted text-sm py-10">
              No results for &ldquo;{query}&rdquo;. Try a different search.
            </p>
          )}

          {matchedDeals.length > 0 && (
            <div className="px-4 pt-3">
              <p className="text-[11px] font-bold text-accent2 uppercase tracking-wide mb-2">Deals</p>
              <div className="space-y-1 mb-3">
                {matchedDeals.map((deal) => (
                  <div
                    key={`deal-${deal.id}`}
                    className="flex items-center justify-between gap-3 px-2 py-2 rounded-lg hover:bg-surface2 transition"
                  >
                    <button onClick={() => goToCategory("deals")} className="flex-1 text-left">
                      <p className="text-sm font-semibold">{deal.name}</p>
                      <p className="text-xs text-muted">Rs. {Number(deal.price).toLocaleString()}</p>
                    </button>
                    <button
                      onClick={() => quickAddDeal(deal)}
                      className="bg-accent hover:bg-accent/90 text-white text-xs font-bold px-3 py-1.5 rounded-full transition shrink-0"
                    >
                      Add
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {matchedItems.length > 0 && (
            <div className="px-4 pb-3">
              <p className="text-[11px] font-bold text-accent2 uppercase tracking-wide mb-2">Menu Items</p>
              <div className="space-y-1">
                {matchedItems.map((item) => {
                  const singlePrice = item.prices?.length === 1 ? item.prices[0] : null;
                  return (
                    <div
                      key={`item-${item.id}`}
                      className="flex items-center justify-between gap-3 px-2 py-2 rounded-lg hover:bg-surface2 transition"
                    >
                      <button onClick={() => goToCategory(item.category)} className="flex-1 text-left">
                        <p className="text-sm font-semibold">{item.name}</p>
                        <p className="text-xs text-muted">
                          {singlePrice
                            ? `Rs. ${Number(singlePrice.price).toLocaleString()}`
                            : `From Rs. ${Number(item.prices?.[0]?.price || 0).toLocaleString()}`}
                        </p>
                      </button>
                      {singlePrice ? (
                        <button
                          onClick={() => quickAddItem(item)}
                          className="bg-accent hover:bg-accent/90 text-white text-xs font-bold px-3 py-1.5 rounded-full transition shrink-0"
                        >
                          Add
                        </button>
                      ) : (
                        <button
                          onClick={() => goToCategory(item.category)}
                          className="text-xs font-bold text-accent2 px-3 py-1.5 shrink-0"
                        >
                          View →
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}