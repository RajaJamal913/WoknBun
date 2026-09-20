"use client";

import { useEffect, useRef, useState, useCallback } from "react";

const GOLD = "#D4A017";

const SLIDES = [
  { id: "1", cta: "Order Now", href: "#beef-burgers", image: "/images/1.png" },
  { id: "2", cta: "Order Now", href: "#appetizers", image: "/images/2.png" },
  { id: "3", cta: "Order Now", href: "#pizza", image: "/images/3.png" },
  { id: "4", cta: "Order Now", href: "#main-course", image: "/images/4.png" },
  { id: "5", cta: "Order Now", href: "#popular", image: "/images/5.png" },
];

const AUTOPLAY_MS = 6000;

export default function HeroSlider() {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const touchStartX = useRef(null);

  const goTo = useCallback((slideIndex) => {
    setIndex((slideIndex + SLIDES.length) % SLIDES.length);
  }, []);

  const next = useCallback(() => setIndex((i) => (i + 1) % SLIDES.length), []);
  const prev = useCallback(() => setIndex((i) => (i - 1 + SLIDES.length) % SLIDES.length), []);

  useEffect(() => {
    if (paused) return;
    const t = setInterval(() => setIndex((i) => (i + 1) % SLIDES.length), AUTOPLAY_MS);
    return () => clearInterval(t);
  }, [paused]);

  return (
    // Inset card, NOT full-bleed. Lives inside your normal page padding.
    <section className="w-full px-4 md:px-6 pt-3">
      <div
        className="relative overflow-hidden w-full h-[160px] md:h-[300px] rounded-2xl shadow-lg"
        style={{ background: "linear-gradient(100deg, #150701 0%, #1b0a02 40%, #050505 75%)" }}
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
        onTouchStart={(e) => (touchStartX.current = e.touches[0].clientX)}
        onTouchEnd={(e) => {
          if (touchStartX.current === null) return;
          const delta = e.changedTouches[0].clientX - touchStartX.current;
          touchStartX.current = null;
          if (Math.abs(delta) > 40) delta < 0 ? next() : prev();
        }}
      >
        {SLIDES.map((s, i) => (
          <div
            key={s.id}
            className="absolute inset-0 transition-opacity duration-700"
            style={{ opacity: i === index ? 1 : 0 }}
          >
            <img
              src={s.image}
              alt=""
              className="absolute inset-0 w-full h-full object-fill"
            />
          </div>
        ))}

        {/* ARROWS */}
        <button
          aria-label="Previous slide"
          onClick={prev}
          style={{ backgroundColor: GOLD }}
          className="absolute left-1.5 md:left-3 top-1/2 -translate-y-1/2 w-6 h-6 md:w-10 md:h-10 text-black text-sm md:text-base rounded-full z-10 flex items-center justify-center shadow-md hover:brightness-110"
        >
          &lsaquo;
        </button>
        <button
          aria-label="Next slide"
          onClick={next}
          style={{ backgroundColor: GOLD }}
          className="absolute right-1.5 md:right-3 top-1/2 -translate-y-1/2 w-6 h-6 md:w-10 md:h-10 text-black text-sm md:text-base rounded-full z-10 flex items-center justify-center shadow-md hover:brightness-110"
        >
          &rsaquo;
        </button>

        {/* ORDER NOW BUTTON */}
        <a
          href={SLIDES[index].href}
          style={{ borderColor: GOLD, color: GOLD }}
          className="absolute bottom-6 left-1/2 -translate-x-1/2 inline-flex items-center gap-2 border-2 bg-black/40 backdrop-blur-sm px-5 py-1.5 rounded-full font-semibold text-xs md:text-sm tracking-wide transition-colors hover:bg-[#D4A017] hover:text-black z-10"
        >
          {SLIDES[index].cta}
        </a>

        {/* DOTS */}
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-2 z-10">
          {SLIDES.map((_, i) => (
            <button
              key={i}
              aria-label={`Go to slide ${i + 1}`}
              aria-current={i === index ? "true" : undefined}
              onClick={() => goTo(i)}
              style={{ backgroundColor: i === index ? GOLD : "rgba(255,255,255,0.4)" }}
              className={`h-1.5 rounded-full transition-all ${i === index ? "w-5" : "w-1.5"}`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}