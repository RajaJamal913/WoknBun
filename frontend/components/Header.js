"use client";

import { useState } from "react";
import { useCart } from "@/context/CartContext";
import { useLocation } from "@/context/LocationContext";
import { useSearch } from "@/context/SearchContext";
import { useUser } from "@/context/UserContext";
import Image from "next/image";

export default function Header() {
  const { itemCount, setDrawerOpen } = useCart();
  const { location, setModalOpen } = useLocation();
  const { setSearchOpen } = useSearch();
  const { user, setAuthOpen, logout } = useUser();
  const [menuOpen, setMenuOpen] = useState(false);

  const iconBtn =
    "inline-flex items-center justify-center w-9 h-9 rounded-full text-muted hover:text-ink hover:bg-white/10 transition";

  return (
    <header className="sticky top-0 z-40 bg-bg/80 backdrop-blur-xl border-b border-white/10">
      <div className="flex items-center justify-between px-4 md:px-8 py-3 max-w-7xl mx-auto">
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-1.5 text-sm text-left min-w-0 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 px-3 py-1.5 transition"
        >
          <svg className="text-accent shrink-0" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z" />
            <circle cx="12" cy="10" r="3" />
          </svg>
          <span className="text-muted hidden sm:inline shrink-0">Delivery to</span>
          <span className="font-semibold text-ink text-xs sm:text-sm truncate max-w-[100px] sm:max-w-[200px]">
            {location ? location.label : "Set your location"}
          </span>
          <span className="text-accent shrink-0 text-xs">▾</span>
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

        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
          <button aria-label="Search" onClick={() => setSearchOpen(true)} className={iconBtn}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
          </button>

          <div className="relative">
            <button
              aria-label={user ? `Account: ${user.full_name}` : "Sign in"}
              onClick={() => (user ? setMenuOpen((v) => !v) : setAuthOpen(true))}
              className={iconBtn}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21a8 8 0 0 0-16 0" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </button>
            {user && menuOpen && (
              <div className="absolute right-0 top-full mt-2 w-44 glass rounded-xl shadow-card overflow-hidden z-20">
                <p className="px-3 py-2 text-xs text-muted border-b border-white/10 truncate">
                  Hi, {user.full_name.split(" ")[0]}
                </p>
                <button
                  onClick={() => {
                    logout();
                    setMenuOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-white/10 transition"
                >
                  Log out
                </button>
              </div>
            )}
          </div>

          <button
            aria-label="Open cart"
            onClick={() => setDrawerOpen(true)}
            className="relative inline-flex items-center justify-center w-10 h-10 rounded-full bg-accent text-white hover:bg-accent-hover shadow-glow active:scale-95 transition"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="9" cy="21" r="1" />
              <circle cx="20" cy="21" r="1" />
              <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
            </svg>
            {itemCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 bg-gold text-black text-[10px] font-extrabold rounded-full min-w-[18px] h-[18px] px-1 flex items-center justify-center ring-2 ring-bg">
                {itemCount}
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}