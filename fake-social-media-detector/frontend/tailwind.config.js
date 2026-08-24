/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["IBM Plex Sans", "ui-sans-serif", "system-ui"],
        display: ["Space Grotesk", "IBM Plex Sans", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      colors: {
        ink: {
          950: "#070b14",
          900: "#0b1220",
          800: "#111a2e",
          700: "#1a2744",
        },
        accent: {
          DEFAULT: "#3ee0c5",
          dim: "#1aa891",
        },
      },
      boxShadow: {
        glow: "0 0 40px rgba(62, 224, 197, 0.12)",
      },
    },
  },
  plugins: [],
};
