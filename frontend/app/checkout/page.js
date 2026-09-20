"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCart } from "@/context/CartContext";
import { createOrder } from "@/lib/api";

export default function CheckoutPage() {
  const router = useRouter();
  const { items, subtotal, tax, deliveryCharges, grandTotal, clearCart } = useCart();

  const [form, setForm] = useState({
    fullName: "",
    mobileNumber: "",
    email: "",
    altPhone: "",
    address: "",
    instructions: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [placedOrder, setPlacedOrder] = useState(null);

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!form.fullName || !form.mobileNumber || !form.address) {
      setError("Please fill in your name, mobile number, and delivery address.");
      return;
    }
    if (items.length === 0) {
      setError("Your cart is empty.");
      return;
    }

    setSubmitting(true);
    try {
      const order = await createOrder({
        full_name: form.fullName,
        mobile_number: form.mobileNumber,
        email: form.email,
        alt_phone: form.altPhone,
        address_line: form.address,
        special_instructions: form.instructions,
        payment_method: "cod",
        items: items.map((i) => ({
          item_name: i.name,
          size_label: i.sizeLabel,
          unit_price: i.unitPrice,
          quantity: i.quantity,
        })),
      });
      setPlacedOrder(order);
      clearCart();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (placedOrder) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center">
        <div className="badge-flame w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">
          ✓
        </div>
        <h1 className="font-display text-2xl mb-2">Order Placed!</h1>
        <p className="text-muted mb-6">
          Order #{placedOrder.id} confirmed. Grand total Rs. {Number(placedOrder.grand_total).toLocaleString()},
          payable by cash on delivery.
        </p>
        <button
          onClick={() => router.push("/")}
          className="bg-accent hover:bg-accent/90 text-white font-bold px-6 py-3 rounded-full transition"
        >
          Back to Menu
        </button>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center">
        <h1 className="font-display text-2xl mb-2">Your cart is empty</h1>
        <p className="text-muted mb-6">Add something delicious before checking out.</p>
        <button
          onClick={() => router.push("/")}
          className="bg-accent hover:bg-accent/90 text-white font-bold px-6 py-3 rounded-full transition"
        >
          Browse Menu
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-8 py-10">
      <p className="text-sm text-muted mb-6">
        <a href="/" className="hover:text-ink">Home</a> <span className="mx-1">›</span> Checkout
      </p>

      <div className="grid md:grid-cols-[1fr_360px] gap-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="bg-surface border border-border rounded-xl p-5 grid sm:grid-cols-2 gap-4">
            <Field label="Full Name" value={form.fullName} onChange={update("fullName")} placeholder="Enter your name" required />
            <Field label="Mobile Number" value={form.mobileNumber} onChange={update("mobileNumber")} placeholder="+92 3XX-XXXXXXX" required />
            <Field label="Email Address (optional)" type="email" value={form.email} onChange={update("email")} placeholder="Enter your email address" />
            <Field label="Alternative Phone (optional)" value={form.altPhone} onChange={update("altPhone")} placeholder="+92 3XX-XXXXXXX" />
          </div>

          <div className="bg-surface border border-border rounded-xl p-5">
            <label className="text-sm font-semibold block mb-2">Delivery Address</label>
            <textarea
              value={form.address}
              onChange={update("address")}
              placeholder="House / street, area, city"
              rows={3}
              required
              className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
            />
          </div>

          <div className="bg-surface border border-border rounded-xl p-5">
            <label className="text-sm font-semibold block mb-2">Special Instructions (Optional)</label>
            <textarea
              value={form.instructions}
              onChange={update("instructions")}
              placeholder="Add any comment, e.g. about allergies or delivery instructions"
              rows={2}
              className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
            />
          </div>

          <div className="bg-surface border border-border rounded-xl p-5">
            <label className="text-sm font-semibold block mb-3">Payment Method</label>
            <div className="inline-flex items-center gap-2 border border-accent text-accent rounded-full px-4 py-2 text-sm font-semibold">
              💵 Cash On Delivery
            </div>
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-accent hover:bg-accent/90 disabled:opacity-60 text-white font-bold py-3 rounded-full transition"
          >
            {submitting ? "Placing Order…" : `Place Order · Rs. ${grandTotal.toLocaleString()}`}
          </button>
        </form>

        <aside className="bg-surface border border-border rounded-xl p-5 h-fit sticky top-32">
          <h2 className="font-display text-lg mb-4">Your Cart</h2>
          <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
            {items.map((item) => (
              <div key={item.key} className="flex justify-between text-sm">
                <div>
                  <p className="font-medium">{item.name}</p>
                  {item.sizeLabel && <p className="text-xs text-muted">{item.sizeLabel}</p>}
                  <p className="text-xs text-muted">Qty {item.quantity}</p>
                </div>
                <span className="text-accent2 font-semibold">
                  Rs. {(item.unitPrice * item.quantity).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
          <div className="border-t border-border mt-4 pt-4 space-y-2 text-sm">
            <div className="flex justify-between text-muted">
              <span>Subtotal</span>
              <span>Rs. {subtotal.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-muted">
              <span>Delivery Charges</span>
              <span>Rs. {deliveryCharges.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-muted">
              <span>Tax (16%)</span>
              <span>Rs. {tax.toLocaleString()}</span>
            </div>
            <div className="flex justify-between font-bold text-base pt-2 border-t border-border">
              <span>Grand Total</span>
              <span className="text-accent2">Rs. {grandTotal.toLocaleString()}</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function Field({ label, ...props }) {
  return (
    <div>
      <label className="text-sm font-semibold block mb-2">{label}</label>
      <input
        {...props}
        className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
      />
    </div>
  );
}