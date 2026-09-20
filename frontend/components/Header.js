"use client";

import { useCart } from "@/context/CartContext";
import { useLocation } from "@/context/LocationContext";
import { useSearch } from "@/context/SearchContext";
import Image from "next/image";

export default function Header() {
  const { itemCount, setDrawerOpen } = useCart();
  const { location, setModalOpen } = useLocation();
  const { setSearchOpen } = useSearch();

  return (
    <header className="sticky top-0 z-40 bg-black/95 backdrop-blur border-b border-[#D4AF37]/30">
      <div className="flex items-center justify-between px-4 md:px-8 py-3 max-w-7xl mx-auto">
        <button onClick={() => setModalOpen(true)} className="flex items-center gap-1.5 text-sm text-left min-w-0">
          <span className="text-[#D4AF37]/60 hidden sm:inline shrink-0">Delivery to</span>
          <span className="font-semibold text-[#D4AF37] text-xs sm:text-sm truncate max-w-[110px] sm:max-w-[220px]">
            {location ? location.label : "Set your location"}
          </span>
          <span className="text-[#D4AF37] shrink-0">▾</span>
        </button>

        <a href="/" className="flex items-center gap-2 shrink-0">
          <Image
            src="/images/logo.png"
            alt="Wok & Bun"
            width={250}
            height={50}
            className="h-9 sm:h-12 md:h-16 w-auto object-contain"
            priority
          />
        </a>

        <div className="flex items-center gap-3 sm:gap-4 shrink-0">
          <button
            aria-label="Search"
            onClick={() => setSearchOpen(true)}
            className="inline-flex text-[#D4AF37]/60 hover:text-[#D4AF37] transition"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
          </button>
          <button
            aria-label="Open cart"
            onClick={() => setDrawerOpen(true)}
            className="relative text-[#D4AF37] hover:text-[#F5D061] transition"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="9" cy="21" r="1" />
              <circle cx="20" cy="21" r="1" />
              <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
            </svg>
            {itemCount > 0 && (
              <span className="absolute -top-2 -right-2 bg-[#D4AF37] text-black text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
                {itemCount}
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}