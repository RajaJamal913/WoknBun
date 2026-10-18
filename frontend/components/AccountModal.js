"use client";

import { useCallback, useEffect, useState } from "react";
import { useUser } from "@/context/UserContext";
import { changeMyPassword, getMyOrders, updateMyProfile } from "@/lib/api";

const inputCls =
  "w-full bg-surface2 border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-accent";
const labelCls = "text-xs font-semibold text-muted block mb-2";
const btnCls = "w-full bg-accent hover:bg-accent/90 disabled:opacity-60 text-white font-bold py-2.5 rounded-full transition text-sm";

const STATUS = {
  pending: "Received",
  confirmed: "Confirmed",
  preparing: "Being prepared",
  out_for_delivery: "On the way",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

const rs = (n) => `Rs. ${Number(n).toLocaleString()}`;

function OrdersTab() {
  const [orders, setOrders] = useState(null); // null = loading
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      setOrders(await getMyOrders());
    } catch (err) {
      setError(err.message);
      setOrders([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (orders === null) return <p className="text-sm text-muted text-center py-8">Loading your orders…</p>;

  return (
    <div className="space-y-3">
      {error && <p className="text-xs text-red-400" role="alert">{error}</p>}
      {orders.length === 0 && !error && (
        <p className="text-sm text-muted text-center py-8">
          No orders yet. Orders you place while signed in appear here, with their progress.
        </p>
      )}
      {orders.map((o) => (
        <div key={o.id} className="bg-surface2 border border-border rounded-xl p-4" data-testid="my-order">
          <div className="flex items-center justify-between mb-2">
            <span className="font-semibold text-sm">Order #{o.id}</span>
            <span className="text-xs font-semibold text-accent2">{STATUS[o.status] || o.status}</span>
          </div>
          <p className="text-xs text-muted mb-2">{new Date(o.created_at).toLocaleString()}</p>
          <ul className="text-sm space-y-0.5 mb-2">
            {o.items.map((i, k) => (
              <li key={k} className="flex justify-between gap-3">
                <span>
                  {i.quantity}× {i.item_name}
                  {i.size_label && i.size_label !== "Regular" ? ` (${i.size_label})` : ""}
                </span>
                <span className="text-muted">{rs(i.line_total)}</span>
              </li>
            ))}
          </ul>
          {o.status === "cancelled" && o.cancel_reason && <p className="text-xs text-red-400 mb-2">Cancelled: {o.cancel_reason}</p>}
          <p className="text-xs text-muted mb-1">Deliver to: {o.address_line}</p>
          <p className="text-sm font-bold text-right">Total {rs(o.grand_total)}</p>
        </div>
      ))}
      <button onClick={load} className="w-full text-xs text-accent2 font-semibold underline underline-offset-2 py-1">
        Refresh
      </button>
    </div>
  );
}

function ProfileTab() {
  const { user, logout } = useUser();
  const [form, setForm] = useState({ fullName: user?.full_name || "", email: user?.email || "", gender: user?.gender || "", dob: user?.date_of_birth || "" });
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [profileMsg, setProfileMsg] = useState({ ok: false, text: "" });
  const [pwMsg, setPwMsg] = useState({ ok: false, text: "" });
  const [busy, setBusy] = useState("");

  async function saveProfile(e) {
    e.preventDefault();
    setProfileMsg({ ok: false, text: "" });
    setBusy("profile");
    try {
      await updateMyProfile({ full_name: form.fullName.trim(), email: form.email.trim(), gender: form.gender, date_of_birth: form.dob || null });
      setProfileMsg({ ok: true, text: "Saved." });
    } catch (err) {
      setProfileMsg({ ok: false, text: err.message });
    } finally {
      setBusy("");
    }
  }

  async function savePassword(e) {
    e.preventDefault();
    setPwMsg({ ok: false, text: "" });
    if (pw.next.length < 8) return setPwMsg({ ok: false, text: "Your new password needs at least 8 characters." });
    if (pw.next !== pw.confirm) return setPwMsg({ ok: false, text: "The two new passwords don't match." });
    setBusy("password");
    try {
      await changeMyPassword(pw.current, pw.next);
      setPw({ current: "", next: "", confirm: "" });
      setPwMsg({ ok: true, text: "Password changed." });
    } catch (err) {
      setPwMsg({ ok: false, text: err.message });
    } finally {
      setBusy("");
    }
  }

  const msg = (m) => m.text && <p className={`text-xs ${m.ok ? "text-green-400" : "text-red-400"}`} role={m.ok ? "status" : "alert"}>{m.text}</p>;

  return (
    <div className="space-y-6">
      <form onSubmit={saveProfile} className="space-y-3">
        <div>
          <label className={labelCls}>Mobile Number</label>
          <input value={user?.phone || ""} disabled className={`${inputCls} opacity-60`} />
          <p className="text-[11px] text-muted mt-1">Your mobile number is your sign-in name, so it can't be changed here.</p>
        </div>
        <div>
          <label className={labelCls}>Full Name</label>
          <input required value={form.fullName} onChange={(e) => setForm((f) => ({ ...f, fullName: e.target.value }))} className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>Email</label>
          <input type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} className={inputCls} />
        </div>
        {msg(profileMsg)}
        <button type="submit" disabled={busy === "profile"} className={btnCls}>{busy === "profile" ? "Saving…" : "Save details"}</button>
      </form>

      <form onSubmit={savePassword} className="space-y-3 border-t border-border pt-5">
        <h3 className="font-display text-base">Change password</h3>
        <input type="password" autoComplete="current-password" placeholder="Current password" value={pw.current} onChange={(e) => setPw((p) => ({ ...p, current: e.target.value }))} className={inputCls} required />
        <input type="password" autoComplete="new-password" placeholder="New password (8+ characters)" value={pw.next} onChange={(e) => setPw((p) => ({ ...p, next: e.target.value }))} className={inputCls} required />
        <input type="password" autoComplete="new-password" placeholder="Confirm new password" value={pw.confirm} onChange={(e) => setPw((p) => ({ ...p, confirm: e.target.value }))} className={inputCls} required />
        {msg(pwMsg)}
        <button type="submit" disabled={busy === "password"} className={btnCls}>{busy === "password" ? "Changing…" : "Change password"}</button>
      </form>

      <button onClick={logout} className="w-full text-sm text-muted hover:text-ink underline underline-offset-2">
        Sign out
      </button>
    </div>
  );
}

export default function AccountModal() {
  const { user, accountOpen, setAccountOpen } = useUser();
  const [tab, setTab] = useState("orders");

  // Back to "My orders" for the next time it opens - done on close, so it can never undo a tab just clicked.
  useEffect(() => {
    if (!accountOpen) setTab("orders");
  }, [accountOpen]);

  if (!accountOpen || !user) return null;
  const close = () => setAccountOpen(false);
  const tabCls = (t) =>
    `flex-1 py-2 text-sm font-semibold rounded-full transition ${tab === t ? "bg-accent text-white" : "text-muted hover:text-ink"}`;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black/80" onClick={close} />
      <div className="relative w-full max-w-md max-h-[92vh] overflow-y-auto bg-surface border border-border rounded-2xl p-6">
        <button onClick={close} aria-label="Close" className="absolute top-4 right-4 text-muted hover:text-ink text-xl leading-none">
          ×
        </button>
        <h2 className="font-display text-xl text-center mb-1">My Account</h2>
        <p className="text-xs text-muted text-center mb-4">{user.full_name}</p>
        <div className="flex gap-1 bg-surface2 rounded-full p-1 mb-5" role="tablist">
          <button role="tab" aria-selected={tab === "orders"} onClick={() => setTab("orders")} className={tabCls("orders")}>My orders</button>
          <button role="tab" aria-selected={tab === "profile"} onClick={() => setTab("profile")} className={tabCls("profile")}>Profile</button>
        </div>
        {tab === "orders" ? <OrdersTab /> : <ProfileTab />}
      </div>
    </div>
  );
}