import { getCategories, getMenuItems, getDeals } from "@/lib/api";
import HeroSlider from "@/components/Heroslider";
import CategoryNav from "@/components/CategoryNav";
import ItemCard from "@/components/ItemCard";
import DealCard from "@/components/DealCard";

export const dynamic = "force-dynamic";

function SectionTitle({ children }) {
  return (
    <h2 className="font-display font-extrabold text-2xl md:text-3xl tracking-tight mb-5 flex items-center gap-3">
      <span className="inline-block w-8 h-1 rounded bg-accent" />
      {children}
    </h2>
  );
}

const SOCIALS = [
  {
    label: "Facebook",
    path: "M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z",
  },
  {
    label: "Instagram",
    path: "M7 2h10a5 5 0 0 1 5 5v10a5 5 0 0 1-5 5H7a5 5 0 0 1-5-5V7a5 5 0 0 1 5-5Zm5 5a5 5 0 1 0 0 10 5 5 0 0 0 0-10Zm5.5-1.5h.01",
  },
  {
    label: "TikTok",
    path: "M9 12a4 4 0 1 0 4 4V3c.5 2.5 2.5 4 5 4",
  },
];

export default async function HomePage() {
  let categories = [];
  let items = [];
  let deals = [];
  let loadError = null;

  try {
    [categories, items, deals] = await Promise.all([getCategories(), getMenuItems(), getDeals()]);
  } catch (e) {
    loadError = e.message;
  }

  if (loadError) {
    return (
      <div className="max-w-xl mx-auto px-4 py-24 text-center">
        <h1 className="font-display font-extrabold text-2xl mb-3">Couldn&apos;t load the menu</h1>
        <p className="text-muted text-sm">
          Make sure the Django API is running at{" "}
          <code className="text-gold">{process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}</code>.
        </p>
      </div>
    );
  }

  const itemsByCategory = categories.map((cat) => ({
    ...cat,
    items: items.filter((item) => item.category === cat.slug),
  })).filter((cat) => cat.items.length > 0);

  return (
    <div>
      {/* Hero slider */}
      <HeroSlider />

      <CategoryNav categories={itemsByCategory} />

      <div className="max-w-7xl mx-auto px-4 md:px-8">
        {/* Deals */}
        {deals.length > 0 && (
          <section id="deals" className="scroll-mt-32 py-10">
            <SectionTitle>
              <span className="text-accent">Deals</span>
            </SectionTitle>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-5">
              {deals.map((deal) => (
                <DealCard key={deal.id} deal={deal} />
              ))}
            </div>
          </section>
        )}

        {/* Menu by category */}
        {itemsByCategory.map((cat) => (
          <section key={cat.slug} id={cat.slug} className="scroll-mt-32 py-10 border-t border-border">
            <SectionTitle>{cat.name}</SectionTitle>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-5">
              {cat.items.map((item) => (
                <ItemCard key={item.id} item={item} />
              ))}
            </div>
          </section>
        ))}
      </div>

      <footer className="bg-surface text-ink mt-10">
        <div className="h-[3px] badge-flame" />
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-12 grid sm:grid-cols-2 md:grid-cols-4 gap-10 text-sm">
          <div className="sm:col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <span className="badge-flame w-9 h-9 rounded-full flex items-center justify-center text-sm">🔥</span>
              <h3 className="font-display font-extrabold text-lg">Wok &amp; Bun</h3>
            </div>
            <p className="text-muted leading-relaxed">
              DHA Phase II Islamabad&apos;s home for gourmet smash burgers, Nashville hot chicken,
              stone-baked pizza and authentic Chinese food — made fresh and delivered hot.
            </p>
            <div className="flex items-center gap-3 mt-4">
              {SOCIALS.map((s) => (
                <a
                  key={s.label}
                  href="#"
                  aria-label={s.label}
                  className="w-9 h-9 rounded-full border border-white/15 flex items-center justify-center text-muted hover:text-white hover:bg-accent hover:border-accent transition"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d={s.path} />
                  </svg>
                </a>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-gold text-xs font-bold uppercase tracking-wider mb-3">Quick Links</h4>
            <ul className="space-y-2 text-muted">
              <li><a href="#deals" className="hover:text-ink transition">Deals</a></li>
              {itemsByCategory.slice(0, 5).map((cat) => (
                <li key={cat.slug}>
                  <a href={`#${cat.slug}`} className="hover:text-ink transition">{cat.name}</a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-gold text-xs font-bold uppercase tracking-wider mb-3">Get Help</h4>
            <ul className="space-y-2 text-muted">
              <li><a href="/checkout" className="hover:text-ink transition">Track an Order</a></li>
              <li><a href="#" className="hover:text-ink transition">Terms &amp; Conditions</a></li>
              <li><a href="#" className="hover:text-ink transition">Privacy Policy</a></li>
              <li><a href="#" className="hover:text-ink transition">Refund Policy</a></li>
            </ul>
          </div>

          <div>
            <h4 className="text-gold text-xs font-bold uppercase tracking-wider mb-3">Visit Us</h4>
            <ul className="space-y-3 text-muted">
              <li className="flex items-start gap-2">
                <span className="text-accent">📍</span>
                <span>DHA Phase II, Islamabad</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-accent">📞</span>
                <span>051-6108530<br />0303 5313933</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-accent">🕒</span>
                <span>Mon – Sun<br />12:00 PM – 04:30 AM</span>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t border-white/10 text-center text-xs text-muted py-4">
          © {new Date().getFullYear()} Wok &amp; Bun. All rights reserved.
        </div>
      </footer>
    </div>
  );
}