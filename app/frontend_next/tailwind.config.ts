import type { Config } from "tailwindcss";

// Colours come from CSS variables (see app/globals.css) so the theme lives in one place.
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Arial", "sans-serif"],
      },
      colors: {
        ink: token("ink"),
        inkSoft: token("ink-soft"),
        muted: token("muted"),
        line: token("line"),
        canvas: token("canvas"),
        panel: token("panel"),
        panelSoft: token("panel-soft"),
        surfaceSoft: token("surface-soft"),
        hover: token("hover"),
        track: token("track"),
        brand: token("brand"),
        brandStrong: token("brand-strong"),
        brandSoft: token("brand-soft"),
        onBrand: token("on-brand"),
        warning: "#b54708",
        danger: "#b42318",
      },
      boxShadow: {
        card: "0 1px 2px rgba(16, 24, 40, .05)",
      },
    },
  },
  plugins: [],
};

export default config;
