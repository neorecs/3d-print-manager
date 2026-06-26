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
        ink: "#17212b",
        muted: "#667085",
        line: "#d9e2e7",
        canvas: "#f6f8fb",
        brand: "#0f766e",
        brandSoft: "#dff7f2",
        warning: "#b45309",
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
