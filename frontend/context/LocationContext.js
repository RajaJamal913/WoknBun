"use client";

import { createContext, useContext, useEffect, useState } from "react";

const LocationContext = createContext(null);
const STORAGE_KEY = "wokandbun_location_v1";

export function LocationProvider({ children }) {
  const [location, setLocationState] = useState(null); // { label, source: "area" | "gps", coords? }
  const [hydrated, setHydrated] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        setLocationState(JSON.parse(raw));
      } else {
        setModalOpen(true); // no saved location yet -> ask on first visit
      }
    } catch (e) {
      setModalOpen(true);
    }
    setHydrated(true);
  }, []);

  function setLocation(loc) {
    setLocationState(loc);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(loc));
    } catch (e) {
      // ignore storage errors
    }
    setModalOpen(false);
  }

  const value = {
    location,
    setLocation,
    hydrated,
    modalOpen,
    setModalOpen,
  };

  return <LocationContext.Provider value={value}>{children}</LocationContext.Provider>;
}

export function useLocation() {
  const ctx = useContext(LocationContext);
  if (!ctx) throw new Error("useLocation must be used within a LocationProvider");
  return ctx;
}