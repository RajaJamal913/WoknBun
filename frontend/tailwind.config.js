/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx}",
    "./components/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0d0b0a",
        surface: "#181413",
        surface2: "#221c1a",
        border: "#332a26",
        accent: {
          DEFAULT: "#ff5a1f",
          hover: "#ff7038",
          deep: "#e0400a",
        },
        gold: "#ffb02e",
        accent2: "#ffb02e",
        muted: "#a8998f",
        ink: "#faf5f0",
      },
      fontFamily: {
        display: ["'Plus Jakarta Sans'", "sans-serif"],
        body: ["Inter", "sans-serif"],
      },
      boxShadow: {
        glow: "0 8px 30px -8px rgba(255,90,31,.45)",
        card: "0 14px 34px -14px rgba(0,0,0,.7)",
      },
    },
  },
  plugins: [],
};