"use client";

import { useEffect, useState } from "react";

export default function CategoryNav({ categories }) {
  const [active, setActive] = useState("deals");

  useEffect(() => {
    const anchors = [{ slug: "deals" }, ...categories];
    const sections = anchors
      .map((a) => document.getElementById(a.slug))
      .filter(Boolean);

    if (sections.length === 0) return;

    // A section is considered "current" when it crosses a thin band just
    // below the sticky header + nav.
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);

        if (visible.length > 0) {
          setActive(visible[0].target.id);
        }
      },
      {
        rootMargin: "-150px 0px -70% 0px",
        threshold: 0,
      }
    );

    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, [categories]);

  function goTo(slug) {
    setActive(slug);
    const el = document.getElementById(slug);
    if (el) {
      const y = el.getBoundingClientRect().top + window.scrollY - 116;
      window.scrollTo({ top: y, behavior: "smooth" });
    }
  }

  const pillBase =
    "whitespace-nowrap px-4 py-2 rounded-full text-sm font-semibold transition border";

  const activeClasses = "bg-accent text-white border-transparent shadow-glow";
  const inactiveClasses =
    "bg-surface2 text-muted border-border hover:text-ink hover:border-accent/50";

  return (
    <nav className="sticky top-[57px] z-30 bg-bg/80 backdrop-blur-xl border-b border-white/10">
      <div className="flex gap-2 overflow-x-auto no-scrollbar px-4 md:px-8 py-3 max-w-7xl mx-auto">
        <button
          onClick={() => goTo("deals")}
          className={`${pillBase} ${active === "deals" ? activeClasses : inactiveClasses}`}
        >
          Deals
        </button>
        {categories.map((cat) => (
          <button
            key={cat.slug}
            onClick={() => goTo(cat.slug)}
            className={`${pillBase} ${active === cat.slug ? activeClasses : inactiveClasses}`}
          >
            {cat.name}
          </button>
        ))}
      </div>
    </nav>
  );
}