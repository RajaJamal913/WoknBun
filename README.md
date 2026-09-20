# Wok & Bun — Online Ordering Site

A food-ordering website for **Wok & Bun** (DHA Phase II, Islamabad), built with:

- **Backend:** Django + Django REST Framework (menu, deals, and order APIs)
- **Frontend:** Next.js (App Router) + Tailwind CSS — black + flame-orange theme

The full menu from your PDF (Appetizers, Wraps, Pizza, Beef & Chicken Burgers,
Pasta, Seafood, Fried Rice, Chow Mein, Main Course, Beverages, and all 10 Deals)
is already loaded as seed data — 55 menu items + 10 deals, with correct
single/size-based pricing (e.g. Single/Double burgers, Small–X-Large pizzas,
Regular/Large mains).

This is a real, runnable project — not a live-hosted demo — because a Django
backend needs its own server. Follow the steps below to run it on your own
machine or a host like Railway / Render / a VPS.

---

## 1. Backend (Django) setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py load_menu      # seeds categories, menu items, prices, deals
python manage.py createsuperuser  # create an admin login to manage the menu

python manage.py runserver 0.0.0.0:8000
```

The API is now live at `http://localhost:8000/api/`:
- `GET /api/categories/`
- `GET /api/menu-items/`
- `GET /api/deals/`
- `POST /api/orders/`

Manage menu items, prices, deals, and view incoming orders at
`http://localhost:8000/admin/` (log in with the superuser you just created).

**To edit prices or add new items later:** either use the Django admin, or
edit `backend/menu/management/commands/load_menu.py` and re-run
`python manage.py load_menu` (this clears and reloads the whole menu, so it's
best for bulk edits before launch — use the admin for day-to-day changes).

## 2. Frontend (Next.js) setup

In a new terminal:

```bash
cd frontend
npm install
cp .env.local.example .env.local   # points the frontend at your Django API
npm run dev
```

Visit `http://localhost:3000`. The homepage fetches categories, menu items,
and deals live from the Django API; adding items builds a cart (persisted in
the browser via localStorage); checkout posts the order to
`POST /api/orders/`, where Django recalculates the subtotal, 16% tax, and
Rs. 250 delivery charge server-side (never trusting the frontend's math) and
stores it so you can see it in `/admin/`.

## 3. What's included / design notes

- **Theme:** black (`#0a0a0b`) base with a flame-orange (`#ff4d1f`) /
  amber (`#ffb020`) accent gradient for badges and CTAs — more modern than
  the teal used on the reference site, and fits Wok & Bun's flame branding.
- **Structure mirrors what worked well in the Cravv review:** sticky category
  pills that scroll to each section, a slide-out cart drawer with live
  subtotal/tax/delivery/total, a sticky mobile "View Cart" bar, and a
  single-page checkout (no multi-step wizard).
- **Fixes applied vs. the issues flagged in the Cravv review:** every item
  has a real price (no Rs. 0.00 placeholders), footer has one Privacy Policy
  link (not duplicated), and the order total is calculated and verified on
  the server, not just trusted from the browser.
- **Not included (intentionally, to keep this a clean starting point):**
  payment gateway integration (Cash on Delivery only, matching your current
  menu's setup), user accounts/login, and product photography — `image_url`
  fields exist on `MenuItem` and `Deal` so you can drop in photos via the
  admin whenever you have them.

## 4. Suggested next steps

- Add real food photography via the Django admin (`image_url` field per item)
- Deploy Django to a host like Railway/Render (Postgres instead of SQLite for
  production) and Next.js to Vercel, pointing `NEXT_PUBLIC_API_URL` at the
  deployed API
- Add WhatsApp/SMS order notifications, or a simple order-status page in the
  Django admin for the kitchen to update `Preparing → Out for Delivery →
  Delivered`
