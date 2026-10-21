/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Newsreader", "Iowan Old Style", "Georgia", "serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      colors: {
        paper: {
          DEFAULT: "#f3efe6",
          raised: "#fbf9f5",
        },
        ink: {
          DEFAULT: "#1c1917",
          soft: "#3f3a36",
        },
        muted: "#6f6860",
        line: "#e3dcd0",
        signal: "#9f2d1f",
        caution: "#8a5a00",
        verified: "#245c3a",
        accent: {
          DEFAULT: "#1c1917",
        },
      },
      maxWidth: {
        prose: "38rem",
      },
    },
  },
  plugins: [],
};
