/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#0A0A0F",
        surface: "#111118",
        panel: "#15151E",
        line: "#2A2A36",
        ink: "#F3F3F5",
        muted: "#9797A8",
        emerald: "#26C281",
        amber: "#F4B942",
        danger: "#F26B4F"
      },
      fontFamily: {
        display: ["Space Grotesk", "Arial", "sans-serif"],
        body: ["DM Sans", "Arial", "sans-serif"],
        mono: ["IBM Plex Mono", "Consolas", "monospace"]
      },
      borderRadius: {
        panel: "10px"
      }
    }
  },
  plugins: []
};
