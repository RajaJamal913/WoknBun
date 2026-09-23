"use client";

import { useEffect, useRef, useState, useCallback } from "react";

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

  const arrow =
    "absolute top-1/2 -translate-y-1/2 z-10 w-8 h-8 md:w-10 md:h-10 rounded-full bg-black/40 backdrop-blur-md border border-white/20 text-white text-lg flex items-center justify-center hover:bg-accent hover:border-accent transition md:opacity-0 md:group-hover:opacity-100";

  return (
    <section className="w-full px-4 md:px-6 pt-3">
      <div
        className="group relative overflow-hidden w-full h-[160px] md:h-[300px] rounded-3xl shadow-card ring-1 ring-white/10 bg-surface"
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
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={s.image} alt="" className="absolute inset-0 w-full h-full object-cover object-center" />
          </div>
        ))}

        {/* Bottom gradient so CTA + dots stay legible */}
        <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/70 to-transparent pointer-events-none" />

        <button aria-label="Previous slide" onClick={prev} className={`${arrow} left-2 md:left-4`}>
          &lsaquo;
        </button>
        <button aria-label="Next slide" onClick={next} className={`${arrow} right-2 md:right-4`}>
          &rsaquo;
        </button>

        <a
          href={SLIDES[index].href}
          className="absolute bottom-6 md:bottom-7 left-1/2 -translate-x-1/2 z-10 inline-flex items-center gap-2 bg-accent text-white px-5 md:px-6 py-1.5 md:py-2 rounded-full font-bold text-xs md:text-sm tracking-wide shadow-glow hover:bg-accent-hover active:scale-95 transition"
        >
          {SLIDES[index].cta} <span aria-hidden>→</span>
        </a>

        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-2 z-10">
          {SLIDES.map((_, i) => (
            <button
              key={i}
              aria-label={`Go to slide ${i + 1}`}
              aria-current={i === index ? "true" : undefined}
              onClick={() => goTo(i)}
              className={`h-1.5 rounded-full transition-all ${
                i === index ? "w-6 bg-accent" : "w-1.5 bg-white/40 hover:bg-white/70"
              }`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}