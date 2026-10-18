"use client";

import { useEffect, useState } from "react";
import { useUser } from "@/context/UserContext";
import { loginCustomer, registerCustomer } from "@/lib/api";

const inputCls =
  "w-full bg-surface2 border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-accent";
const labelCls = "text-xs font-semibold text-muted block mb-2";

export default function AuthModal() {
  const { authOpen, setAuthOpen } = useUser();
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [showPw, setShowPw] = useState(false);

  const [login, setLogin] = useState({ identifier: "", password: "" });
  const [form, setForm] = useState({ fullName: "", mobile: "", email: "", gender: "", dob: "", password: "", confirm: "" });

  // The modal never unmounts (it just hides). Reset it when it CLOSES, so the next opening is already
  // clean. (Resetting on open would race with autofill / password managers and wipe what they typed.)
  useEffect(() => {
    if (!authOpen) {
      setMode("login");
      setError("");
      setShowPw(false);
      setLogin({ identifier: "", password: "" });
      setForm({ fullName: "", mobile: "", email: "", gender: "", dob: "", password: "", confirm: "" });
    }
  }, [authOpen]);

  if (!authOpen) return null;

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  const close = () => {
    setAuthOpen(false);
    setError("");
  };
  const switchTo = (next) => {
    setMode(next);
    setError("");
  };

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await loginCustomer(login.identifier.trim(), login.password);
      setAuthOpen(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    setError("");
    if (!form.fullName.trim() || !form.mobile.trim()) {
      setError("Please enter your name and mobile number.");
      return;
    }
    if (form.password.length < 8) {
      setError("Your password needs at least 8 characters.");
      return;
    }
    if (form.password !== form.confirm) {
      setError("The two passwords don't match.");
      return;
    }
    setSubmitting(true);
    try {
      await registerCustomer({
        full_name: form.fullName.trim(),
        phone: form.mobile.trim(),
        email: form.email.trim(),
        gender: form.gender,
        date_of_birth: form.dob || null,
        password: form.password,
      });
      setAuthOpen(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const pwType = showPw ? "text" : "password";
  const submitCls =
    "w-full bg-accent hover:bg-accent/90 disabled:opacity-60 text-white font-bold py-3 rounded-full transition";
  const linkBtn = "text-accent2 font-semibold underline underline-offset-2";

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black/80" onClick={close} />
      <div className="relative w-full max-w-sm max-h-[92vh] overflow-y-auto bg-surface border border-border rounded-2xl p-6">
        <button onClick={close} aria-label="Close" className="absolute top-4 right-4 text-muted hover:text-ink text-xl leading-none">
          ×
        </button>

        <h2 className="font-display text-xl text-center mb-5">{mode === "login" ? "Sign In" : "Create Account"}</h2>

        {mode === "login" ? (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className={labelCls}>Mobile Number or Email</label>
              <input
                required
                autoComplete="username"
                value={login.identifier}
                onChange={(e) => setLogin((l) => ({ ...l, identifier: e.target.value }))}
                placeholder="03XX-XXXXXXX or you@example.com"
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Password</label>
              <input
                required
                type={pwType}
                autoComplete="current-password"
                value={login.password}
                onChange={(e) => setLogin((l) => ({ ...l, password: e.target.value }))}
                className={inputCls}
              />
            </div>
            <label className="flex items-center gap-2 text-xs text-muted">
              <input type="checkbox" checked={showPw} onChange={(e) => setShowPw(e.target.checked)} /> Show password
            </label>

            {error && <p className="text-xs text-red-400" role="alert">{error}</p>}

            <button type="submit" disabled={submitting} className={submitCls}>
              {submitting ? "Signing In…" : "Sign In"}
            </button>

            <p className="text-center text-xs text-muted">
              Forgot your password? Call us and we'll reset your login, then you can register again.
            </p>
            <p className="text-center text-xs text-muted">
              New here?{" "}
              <button type="button" onClick={() => switchTo("register")} className={linkBtn}>
                Create an account
              </button>
            </p>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className={labelCls}>Full Name</label>
              <input required autoComplete="name" value={form.fullName} onChange={update("fullName")} placeholder="Enter your name" className={inputCls} />
            </div>

            <div>
              <label className={labelCls}>Mobile Number</label>
              <div className="flex gap-2">
                <span className="bg-surface2 border border-border rounded-lg px-3 py-2.5 text-sm text-muted shrink-0">+92</span>
                <input
                  required
                  type="tel"
                  autoComplete="tel"
                  value={form.mobile}
                  onChange={update("mobile")}
                  placeholder="3XX-XXXXXXX"
                  className="flex-1 min-w-0 bg-surface2 border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-accent"
                />
              </div>
              <p className="text-[11px] text-muted mt-1">This is what you'll sign in with.</p>
            </div>

            <div>
              <label className={labelCls}>
                Email Address <span className="font-normal">(Optional)</span>
              </label>
              <input type="email" autoComplete="email" value={form.email} onChange={update("email")} placeholder="you@example.com" className={inputCls} />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>
                  Gender <span className="font-normal">(Optional)</span>
                </label>
                <select value={form.gender} onChange={update("gender")} className={inputCls}>
                  <option value="">Select</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>
                  Date of Birth <span className="font-normal">(Optional)</span>
                </label>
                <input type="date" value={form.dob} onChange={update("dob")} className={inputCls} />
              </div>
            </div>

            <div>
              <label className={labelCls}>Password</label>
              <input required type={pwType} autoComplete="new-password" value={form.password} onChange={update("password")} placeholder="At least 8 characters" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Confirm Password</label>
              <input required type={pwType} autoComplete="new-password" value={form.confirm} onChange={update("confirm")} className={inputCls} />
            </div>
            <label className="flex items-center gap-2 text-xs text-muted">
              <input type="checkbox" checked={showPw} onChange={(e) => setShowPw(e.target.checked)} /> Show passwords
            </label>

            {error && <p className="text-xs text-red-400" role="alert">{error}</p>}

            <button type="submit" disabled={submitting} className={submitCls}>
              {submitting ? "Creating account…" : "Create Account"}
            </button>

            <p className="text-center text-xs text-muted">
              Already have an account?{" "}
              <button type="button" onClick={() => switchTo("login")} className={linkBtn}>
                Sign in
              </button>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}