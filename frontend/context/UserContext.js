"use client";

import { createContext, useContext, useEffect, useState } from "react";

const UserContext = createContext(null);
const STORAGE_KEY = "wokandbun_user_v1";

export function UserProvider({ children }) {
  const [user, setUserState] = useState(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) setUserState(JSON.parse(raw));
    } catch (e) {
      // ignore corrupt storage
    }
    setHydrated(true);
  }, []);

  function setUser(customer) {
    setUserState(customer);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(customer));
    } catch (e) {
      // ignore storage errors
    }
    setAuthOpen(false);
  }

  function logout() {
    setUserState(null);
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      // ignore
    }
  }

  const value = { user, setUser, logout, authOpen, setAuthOpen, hydrated };

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be used within a UserProvider");
  return ctx;
}