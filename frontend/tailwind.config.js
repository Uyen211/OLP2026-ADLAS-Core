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
      },
      borderRadius: {
        pill: "9999px",
      },
      boxShadow: {
        brand: "0 4px 14px 0 rgba(20, 86, 240, 0.15)",
        card: "0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)",
      },
    },
  },
  plugins: [],
};
