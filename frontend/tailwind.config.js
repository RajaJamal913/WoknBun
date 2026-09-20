/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx}",
    "./components/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0b",
        surface: "#151517",
        surface2: "#1e1e21",
        border: "#2a2a2e",
        accent: "#c8960c",
        accent2: "#f0c419",
        muted: "#9a9aa1",
        ink: "#f2f2f3",
      },
      fontFamily: {
        display: ["'Archivo Black'", "sans-serif"],
        body: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
};