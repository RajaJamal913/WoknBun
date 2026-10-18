"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { clearSession, getSession, subscribe } from "@/lib/session";

const UserContext = createContext(null);

export function UserProvider({ children }) {
  const [user, setUser] = useState(null); // the signed-in customer's profile, or null
  const [hydrated, setHydrated] = useState(false);
  const [authOpen, setAuthOpen] = useState(false); // sign in / register
  const [accountOpen, setAccountOpen] = useState(false); // my orders / profile

  useEffect(() => {
    setUser(getSession()?.customer || null);
    setHydrated(true);
    // Stays in step with session.js (sign in, sign out, a session that expired, another tab...).
    return subscribe((session) => {
      setUser(session?.customer || null);
      if (!session) setAccountOpen(false);
    });
  }, []);

  function logout() {
    clearSession();
    setAccountOpen(false);
  }

  const value = { user, hydrated, authOpen, setAuthOpen, accountOpen, setAccountOpen, logout };
  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be used within a UserProvider");
  return ctx;
}