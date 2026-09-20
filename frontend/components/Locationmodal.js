"use client";

import { useState } from "react";
import Image from "next/image";
import { useLocation } from "@/context/LocationContext";

// Areas within roughly 50km of DHA Phase II, Islamabad.
// Grouped so the dropdown is easier to scan; adjust freely as your
// actual delivery radius or rider coverage changes.
const AREA_GROUPS = [
  {
    group: "DHA & Bahria Town",
    areas: [
      "DHA Phase I, Islamabad",
      "DHA Phase II, Islamabad",
      "DHA Phase III, Islamabad",
      "DHA Phase IV, Islamabad",
      "DHA Phase V, Islamabad",
      "Bahria Town Phase 1, Rawalpindi",
      "Bahria Town Phase 2, Rawalpindi",
      "Bahria Town Phase 3, Rawalpindi",
      "Bahria Town Phase 4, Rawalpindi",
      "Bahria Town Phase 5, Rawalpindi",
      "Bahria Town Phase 6, Rawalpindi",
      "Bahria Town Phase 7, Rawalpindi",
      "Bahria Town Phase 8, Rawalpindi",
    ],
  },
  {
    group: "Islamabad Sectors",
    areas: [
      "Jinnah Garden, Islamabad",
      "Karal, Islamabad",
      "Humak , Islamabad",
      "PWD Housing Society, Islamabad",
      "Gulberg Greens, Islamabad",
      "Soan Garden, Islamabad",
      "CBR Town, Islamabad",
      "Media Town, Islamabad",
      "Airport Housing Society, Islamabad",
    ],
  },
  {
    group: "Rawalpindi & Cantt",
    areas: [
      "Askari 10, Rawalpindi",
      "Askari 11, Rawalpindi",
      "Askari 14, Rawalpindi",
     
    ],
  },
  {
    group: "Further Out (~40–50km)",
    areas: ["Taxila", "Wah Cantt"],
  },
];

// Approximate coordinates for DHA Phase II, Islamabad (near Giga Mall / Sector F).
const CAFE_LOCATION = { lat: 33.5344, lng: 73.1543 };
const DELIVERY_RADIUS_KM = 50;

// Haversine formula: great-circle distance between two lat/lng points, in km.
function distanceKm(lat1, lng1, lat2, lng2) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export default function LocationModal() {
  const { modalOpen, setModalOpen, setLocation } = useLocation();
  const [selectedArea, setSelectedArea] = useState("");
  const [locating, setLocating] = useState(false);
  const [gpsError, setGpsError] = useState("");

  if (!modalOpen) return null;

  function handleConfirm() {
    if (!selectedArea) return;
    setLocation({ label: selectedArea, source: "area" });
  }

  function handleUseCurrentLocation() {
    if (!navigator.geolocation) {
      setGpsError("Location isn't supported on this browser. Please pick your area below.");
      return;
    }
    setGpsError("");
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        const { latitude, longitude } = pos.coords;
        const distance = distanceKm(CAFE_LOCATION.lat, CAFE_LOCATION.lng, latitude, longitude);

        if (distance > DELIVERY_RADIUS_KM) {
          setGpsError(
            `Sorry, we don't deliver to your location yet — you're about ${Math.round(
              distance
            )}km from our DHA Phase II cafe, and we currently deliver within ${DELIVERY_RADIUS_KM}km. Please pick the closest area below instead.`
          );
          return;
        }

        setLocation({
          label: "Current Location",
          source: "gps",
          coords: { lat: latitude, lng: longitude },
        });
      },
      () => {
        setLocating(false);
        setGpsError("Couldn't access your location. Please pick your area below instead.");
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/80" />
      <div className="relative w-full max-w-sm bg-surface border border-border rounded-2xl p-6 flex flex-col items-center text-center gap-4">
        <Image
          src="/images/logo.png"
          alt="Wok & Bun"
          width={200}
          height={60}
          className="h-16 w-auto object-contain"
          priority
        />
        <div>
          <p className="text-muted text-sm mt-1">
            Delivering from DHA Phase II, Islamabad — where should we send your order?
          </p>
        </div>

        <button
          onClick={handleUseCurrentLocation}
          disabled={locating}
          className="w-full flex items-center justify-center gap-2 border border-border hover:border-accent rounded-full py-2.5 text-sm font-semibold transition disabled:opacity-60"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
          </svg>
          {locating ? "Detecting your location…" : "Use Current Location"}
        </button>

        {gpsError && (
          <div className="w-full bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2.5 text-left">
            <p className="text-xs text-red-400 leading-relaxed">{gpsError}</p>
          </div>
        )}

        <div className="flex items-center gap-3 w-full text-muted text-xs">
          <div className="flex-1 h-px bg-border" />
          OR
          <div className="flex-1 h-px bg-border" />
        </div>

        <div className="w-full text-left">
          <label className="text-xs font-semibold text-muted block mb-2">
            Select Area / Sub Region
          </label>
          <select
            value={selectedArea}
            onChange={(e) => setSelectedArea(e.target.value)}
            className="w-full bg-surface2 border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-accent"
          >
            <option value="">Choose your area…</option>
            {AREA_GROUPS.map((g) => (
              <optgroup key={g.group} label={g.group}>
                {g.areas.map((area) => (
                  <option key={area} value={area}>
                    {area}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        <button
          onClick={handleConfirm}
          disabled={!selectedArea}
          className="w-full bg-accent hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold py-3 rounded-full transition"
        >
          Confirm Location
        </button>

        <button
          onClick={() => setModalOpen(false)}
          className="text-xs text-muted hover:text-ink underline underline-offset-2"
        >
          Skip for now
        </button>
      </div>
    </div>
  );
}