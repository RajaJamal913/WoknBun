"use client";

import { useEffect, useState } from "react";
import { useUser } from "@/context/UserContext";
import { registerCustomer, loginCustomer } from "@/lib/api";

export default function AuthModal() {
  const { authOpen, setAuthOpen, setUser } = useUser();
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [loginEmail, setLoginEmail] = useState("");
  const [form, setForm] = useState({
    fullName: "",
    email: "",
    gender: "",
    dob: "",
    mobile: "",
  });

  // The modal never unmounts (it just hides), so reset to a clean Sign-In
  // view and clear stale field values every time it's opened again.
  useEffect(() => {
    if (authOpen) {
      setMode("login");
      setError("");
      setLoginEmail("");
      setForm({ fullName: "", email: "", gender: "", dob: "", mobile: "" });
    }
  }, [authOpen]);

  if (!authOpen) return null;

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  function close() {
    setAuthOpen(false);
    setError("");
  }

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    if (!loginEmail) return;
    setSubmitting(true);
    try {
      const customer = await loginCustomer(loginEmail);
      setUser(customer);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    setError("");
    if (!form.fullName || !form.email || !form.mobile) {
      setError("Please fill in your name, email, and mobile number.");
      return;
    }
    setSubmitting(true);
    try {
      const customer = await registerCustomer({
        full_name: form.fullName,
        email: form.email,
        gender: form.gender,
        date_of_birth: form.dob || null,
        mobile_number: form.mobile,
      });
      setUser(customer);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/80" onClick={close} />
      <div className="relative w-full max-w-sm bg-surface border border-border rounded-2xl p-6">
        <button
          onClick={close}
          aria-label="Close"
          className="absolute top-4 right-4 text-muted hover:text-ink text-xl leading-none"
        >
          ×
        </button>

        <h2 className="font-display text-xl text-center mb-5">
          {mode === "login" ? "Sign In" : "Register"}
        </h2>

        {mode === "login" ? (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-muted block mb-2">Email Address</label>
              <input
                type="email"
                required
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full bg-surface2 border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-accent"
              />
            </div>

            {error && <p className="text-xs text-red-400">{error}</p>}

            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-accent hover:bg-accent/90 disabled:opacity-60 text-white font-bold py-3 rounded-full transition"
            >
              {submitting ? "Signing In…" : "Sign In"}
            </button>

            <p className="text-center text-xs text-muted">
              New here?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("register");
                  setError("");
                }}
                className="text-accent2 font-semibold underline underline-offset-2"
              >
                Create an account
              </button>
            </p>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-muted block mb-2">Full Name</label>
              <input
                required
                value={form.fullName}
                onChange={update("fullName")}
                placeholder="Enter your name"
                className="w-full bg-surface2 border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-accent"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-muted block mb-2">Email Address</label>
              <input
                type="email"
                required
                value={form.email}
                onChange={update("email")}
                placeholder="you@example.com"
                className="w-full bg-surface2 border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-accent"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-muted block mb-2">
                  Gender <span className="font-normal">(Optional)</span>
                </label>
                <select
                  value={form.gender}
                  onChange={update("gender")}
                  className="w-full bg-surface2 border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-accent"
                >
                  <option value="">Select</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-muted block mb-2">
                  Date of Birth <span className="font-normal">(Optional)</span>
                </label>
                <input
                  type="date"
                  value={form.dob}
                  onChange={update("dob")}
                  className="w-full bg-surface2 border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-accent"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted block mb-2">Mobile Number</label>
              <div className="flex gap-2">
                <span className="bg-surface2 border border-border rounded-lg px-3 py-2.5 text-sm text-muted shrink-0">
                  +92
                </span>
                <input
                  required
                  value={form.mobile}
                  onChange={update("mobile")}
                  placeholder="3XX-XXXXXXX"
                  className="flex-1 min-w-0 bg-surface2 border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-accent"
                />
              </div>
            </div>

            {error && <p className="text-xs text-red-400">{error}</p>}

            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-accent hover:bg-accent/90 disabled:opacity-60 text-white font-bold py-3 rounded-full transition"
            >
              {submitting ? "Registering…" : "Register"}
            </button>

            <p className="text-center text-xs text-muted">
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("login");
                  setError("");
                }}
                className="text-accent2 font-semibold underline underline-offset-2"
              >
                Sign in
              </button>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}