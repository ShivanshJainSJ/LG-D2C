import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        livguard: {
          red: "#E31E24",
          redDark: "#B91C1C",
          redLight: "#FEE2E2",
          black: "#000000",
          dark: "#111827",
          charcoal: "#1F2937",
          gray: "#4B5563",
          lightGray: "#F3F4F6",
          green: "#16A34A",
          greenLight: "#DCFCE7",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
