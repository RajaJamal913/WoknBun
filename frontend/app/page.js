import { getCategories, getMenuItems, getDeals } from "@/lib/api";
import HeroSlider from "@/components/HeroSlider";
import CategoryNav from "@/components/CategoryNav";
import ItemCard from "@/components/ItemCard";
import DealCard from "@/components/DealCard";

export const dynamic = "force-dynamic";

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
        <h1 className="font-display text-2xl mb-3">Couldn&apos;t load the menu</h1>
        <p className="text-muted text-sm">
          Make sure the Django API is running at{" "}
          <code className="text-accent2">{process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}</code>.
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
            <h2 className="font-display text-2xl mb-4">
              <span className="text-accent">DEALS</span>
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {deals.map((deal) => (
                <DealCard key={deal.id} deal={deal} />
              ))}
            </div>
          </section>
        )}

        {/* Menu by category */}
        {itemsByCategory.map((cat) => (
          <section key={cat.slug} id={cat.slug} className="scroll-mt-32 py-10 border-t border-border">
            <h2 className="font-display text-2xl mb-5">{cat.name.toUpperCase()}</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {cat.items.map((item) => (
                <ItemCard key={item.id} item={item} />
              ))}
            </div>
          </section>
        ))}
      </div>

      <footer className="bg-black text-white mt-10">
        <div className="h-[3px] badge-flame" />
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-12 grid sm:grid-cols-2 md:grid-cols-4 gap-10 text-sm">
          <div className="sm:col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <span className="badge-flame w-8 h-8 rounded-full flex items-center justify-center text-sm">🔥</span>
              <h3 className="font-display text-lg">WOK & BUN</h3>
            </div>
            <p className="text-white/50 leading-relaxed">
              DHA Phase II Islamabad&apos;s home for gourmet smash burgers, Nashville hot chicken,
              stone-baked pizza and authentic Chinese food — made fresh and delivered hot.
            </p>
            <div className="flex items-center gap-3 mt-4">
              {["Facebook", "Instagram", "TikTok"].map((label) => (
                <a
                  key={label}
                  href="#"
                  aria-label={label}
                  className="w-8 h-8 rounded-full border border-white/20 flex items-center justify-center text-white/60 hover:text-accent hover:border-accent transition"
                >
                  <span className="text-xs font-bold">{label[0]}</span>
                </a>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-accent2 text-xs font-bold uppercase tracking-wider mb-3">Quick Links</h4>
            <ul className="space-y-2 text-white/60">
              <li><a href="#deals" className="hover:text-white transition">Deals</a></li>
              {itemsByCategory.slice(0, 5).map((cat) => (
                <li key={cat.slug}>
                  <a href={`#${cat.slug}`} className="hover:text-white transition">{cat.name}</a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-accent2 text-xs font-bold uppercase tracking-wider mb-3">Get Help</h4>
            <ul className="space-y-2 text-white/60">
              <li><a href="/checkout" className="hover:text-white transition">Track an Order</a></li>
              <li><a href="#" className="hover:text-white transition">Terms & Conditions</a></li>
              <li><a href="#" className="hover:text-white transition">Privacy Policy</a></li>
              <li><a href="#" className="hover:text-white transition">Refund Policy</a></li>
            </ul>
          </div>

          <div>
            <h4 className="text-accent2 text-xs font-bold uppercase tracking-wider mb-3">Visit Us</h4>
            <ul className="space-y-3 text-white/60">
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
                <span>Mon – Sun<br />12:00 PM – 01:30 AM</span>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t border-white/10 text-center text-xs text-white/40 py-4">
          © {new Date().getFullYear()} Wok & Bun. All rights reserved.
        </div>
      </footer>
    </div>
  );
}