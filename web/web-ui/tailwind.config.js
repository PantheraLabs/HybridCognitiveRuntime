/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#09090b", // zinc-950
        foreground: "#fafafa", // zinc-50
        card: "#18181b", // zinc-900
        cardForeground: "#fafafa",
        border: "#27272a", // zinc-800
        input: "#27272a",
        primary: {
          DEFAULT: "#f4f4f5", // zinc-100
          foreground: "#18181b", // zinc-900
        },
        secondary: {
          DEFAULT: "#27272a",
          foreground: "#fafafa",
        },
        accent: {
          DEFAULT: "#27272a",
          foreground: "#fafafa",
        },
        destructive: {
          DEFAULT: "#7f1d1d", // red-900
          foreground: "#fef2f2", // red-50
        },
        ring: "#d4d4d8", // zinc-300
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      }
    },
  },
  plugins: [],
}
