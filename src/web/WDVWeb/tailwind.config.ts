import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/context/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        /* Matches RPi kiosk theme.py palette exactly */
        aqua: "#00a8ff",
        accent: "#2ecc71",
        danger: "#e74c3c",
        "dark-blue": "#0277bd",
        "screen-bg": "#e1f5fe",
        "sidebar-bg": "#01579b",
        "app-bg": "#1a2744",
        steel: "#7f8c8d",
        warning: "#f39c12",
        cold: "#039be5",
        warm: "#ffb300",
        hot: "#f4511e",
      },
    },
  },
  plugins: [],
};

export default config;
