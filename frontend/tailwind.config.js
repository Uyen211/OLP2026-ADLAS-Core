/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          deep: "#17437d",
          primary: "#1456f0",
          sky: "#3daeff",
          light: "#bfdbfe",
          pink: "#ea5ec1",
        },
        surface: {
          base: "#ffffff",
          muted: "#f8fafc",
          subtle: "#f1f5f9",
          dark: "#181e25",
        },
        content: {
          primary: "#1e293b",
          secondary: "#475569",
          muted: "#94a3b8",
        },
        mm: {
          surface: "#ffffff",
          "surface-alt": "#f8fafc",
          brand: "#1456f0",
          "brand-light": "#eff6ff",
          error: "#d92d20",
          "error-bg": "#fef2f2",
          bg: "#ffffff",
          "btn-secondary": "#f0f0f0",
          divider: "#f2f3f5",
          border: "#e5e7eb",
          "success-bg": "#e8ffea",
          success: "#15803d",
          dark: "#181e25",
          "blue-primary": "#1456f0",
          "blue-sky": "#3daeff",
          "blue-light": "#bfdbfe",
          "blue-400": "#60a5fa",
          "blue-500": "#3b82f6",
          "blue-hover": "#2563eb",
          "blue-active": "#1d4ed8",
          "blue-deep": "#17437d",
          text: "#222222",
          heading: "#18181b",
          "text-secondary": "#45515e",
          "text-muted": "#8e8e93",
          "text-helper": "#5f5f5f",
          danger: "#d92d20",
          "danger-bg": "#fef2f2",
          "warning-bg": "#fff7e6",
          warning: "#b54708",
        },
      },
      fontFamily: {
        "mm-ui": ['"DM Sans"', "sans-serif"],
        "mm-display": ['"Outfit"', "sans-serif"],
        "mm-mid": ['"Poppins"', "sans-serif"],
        "mm-data": ['"Roboto"', "sans-serif"],
        "mm-mono": ['"JetBrains Mono"', "monospace"],
      },
      borderRadius: {
        pill: "9999px",
        mm: "12px",
        "mm-lg": "16px",
        "mm-tag": "4px",
        "mm-btn": "8px",
        "mm-panel": "13px",
        "mm-card": "20px",
        "mm-card-lg": "24px",
      },
      boxShadow: {
        brand: "0 4px 14px 0 rgba(20, 86, 240, 0.15)",
        card: "0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)",
        "mm-standard": "0 4px 6px rgba(0, 0, 0, 0.08)",
        "mm-ambient": "0 0 22.576px rgba(0, 0, 0, 0.08)",
        "mm-brand": "0 0 15px rgba(44, 30, 116, 0.16)",
        "mm-elevated": "0 12px 16px -4px rgba(36, 36, 36, 0.08)",
      },
    },
  },
  plugins: [],
};
