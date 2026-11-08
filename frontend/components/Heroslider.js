"use client";

import { useEffect, useReducer, useState, useRef, useCallback } from "react";

// Each slide is an animated banner (public/banners/N.html + public/banners/assets/N-*.{jpg,png,webp}).
// The banner is rendered in an iframe that is re-mounted every time its slide becomes active,
// so the animation always starts from the beginning when the slide appears.
const SLIDES = [
  { id: "1", cta: "Order Now", href: "#beef-burgers", banner: "/banners/1.html" },
  { id: "2", cta: "Order Now", href: "#appetizers", banner: "/banners/2.html" },
  { id: "3", cta: "Order Now", href: "#pizza", banner: "/banners/3.html" },
  { id: "4", cta: "Order Now", href: "#main-course", banner: "/banners/4.html" },
  { id: "5", cta: "Order Now", href: "#popular", banner: "/banners/5.html" },
];

// Banners need ~5s to finish their intro animation, so give each slide a bit longer than before.
const AUTOPLAY_MS = 9000;
// The slider keeps the banner artwork's own proportions so the complete image is always visible (no cropping).
const BANNER_ASPECT = "2172 / 724";

function reducer(state, action) {
  if (action.type === "clear") return { ...state, leaving: null };
  const n = (action.to + SLIDES.length) % SLIDES.length;
  if (n === state.index) return state;
  const runs = state.runs.slice();
  runs[n] += 1; // new key => the iframe is re-mounted => animation restarts
  return { index: n, leaving: state.index, runs };
}

export default function HeroSlider() {
  const [{ index, leaving, runs }, dispatch] = useReducer(reducer, {
    index: 0,
    leaving: null,
    runs: SLIDES.map((_, i) => (i === 0 ? 1 : 0)),
  });
  const [paused, setPaused] = useState(false);
  const touchStartX = useRef(null);

  const goTo = useCallback((i) => dispatch({ type: "go", to: i }), []);
  const next = useCallback(() => dispatch({ type: "go", to: index + 1 }), [index]);
  const prev = useCallback(() => dispatch({ type: "go", to: index - 1 }), [index]);

  useEffect(() => {
    if (paused) return;
    const t = setInterval(() => dispatch({ type: "go", to: index + 1 }), AUTOPLAY_MS);
    return () => clearInterval(t);
  }, [paused, index]);

  // keep the outgoing slide mounted until the cross-fade has finished
  useEffect(() => {
    if (leaving === null) return;
    const t = setTimeout(() => dispatch({ type: "clear" }), 800);
    return () => clearTimeout(t);
  }, [leaving]);

  const arrow =
    "absolute top-1/2 -translate-y-1/2 z-10 w-8 h-8 md:w-10 md:h-10 rounded-full bg-black/40 backdrop-blur-md border border-white/20 text-white text-lg flex items-center justify-center hover:bg-accent hover:border-accent transition md:opacity-0 md:group-hover:opacity-100";

  return (
    <section className="w-full px-4 md:px-6 pt-3">
      <div
        className="group relative overflow-hidden w-full rounded-3xl shadow-card ring-1 ring-white/10 bg-surface"
        style={{ aspectRatio: BANNER_ASPECT }}
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
            aria-hidden={i !== index}
          >
            {(i === index || i === leaving) && (
              <iframe
                key={`${s.id}-${runs[i]}`}
                src={s.banner}
                title=""
                tabIndex={-1}
                scrolling="no"
                sandbox="allow-scripts"
                className="absolute inset-0 w-full h-full border-0 block pointer-events-none"
              />
            )}
          </div>
        ))}

        {/* Bottom gradient so CTA + dots stay legible */}
        <div className="absolute inset-x-0 bottom-0 h-14 bg-gradient-to-t from-black/50 to-transparent pointer-events-none" />

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
