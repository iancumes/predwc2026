import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Dark "stadium at night" surface palette.
        base: {
          DEFAULT: "#070b16",
          900: "#0a0f1f",
          800: "#0e1528",
          700: "#141d36",
          600: "#1c2746",
        },
        // Signature electric accents (move away from the flat green).
        brand: {
          DEFAULT: "#22d3a6", // mint-emerald
          300: "#6ee7c7",
          400: "#34e0b4",
          600: "#10b98a",
        },
        electric: "#38bdf8", // cyan
        violet: "#a855f7",
        magenta: "#f43f7e",
        gold: "#fbbf24",
        ink: "#0f172a",
        // Back-compat aliases (older markup referenced these tokens).
        pitch: { DEFAULT: "#0b3d2e", light: "#11533f" },
        accent: { DEFAULT: "#22d3a6", soft: "#6ee7c7" },
      },
      fontFamily: {
        display: ["var(--font-display)", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(34,211,166,0.25), 0 8px 40px -8px rgba(34,211,166,0.35)",
        card: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 12px 40px -16px rgba(0,0,0,0.7)",
        lift: "0 20px 60px -20px rgba(0,0,0,0.8)",
      },
      backgroundImage: {
        "grid-faint":
          "linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)",
        "brand-gradient":
          "linear-gradient(120deg, #22d3a6 0%, #38bdf8 55%, #a855f7 100%)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(14px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        "scale-in": {
          "0%": { opacity: "0", transform: "translateY(12px) scale(0.96)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        "slide-in-right": {
          "0%": { opacity: "0", transform: "translateX(24px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "bar-grow": {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s cubic-bezier(0.22,1,0.36,1) both",
        "fade-in": "fade-in 0.4s ease both",
        "scale-in": "scale-in 0.28s cubic-bezier(0.22,1,0.36,1) both",
        "slide-in-right": "slide-in-right 0.35s cubic-bezier(0.22,1,0.36,1) both",
        "bar-grow": "bar-grow 0.7s cubic-bezier(0.22,1,0.36,1) both",
        shimmer: "shimmer 2.2s linear infinite",
        float: "float 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
