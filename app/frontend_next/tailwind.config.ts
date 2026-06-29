import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#eef6ff",
        muted: "#8ea0b6",
        line: "#223047",
        canvas: "#070b12",
        panel: "#0d1422",
        panelSoft: "#111b2d",
        brand: "#2dd4bf",
        brandSoft: "#123c3b",
        warning: "#b45309",
        danger: "#b42318",
      },
      boxShadow: {
        card: "0 18px 60px rgba(0, 0, 0, .28)",
      },
    },
  },
  plugins: [],
};

export default config;
