/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // `bg-card` / `text-muted-foreground` are used by LineChart.tsx and
      // OrderBook.tsx but were never defined, so Tailwind silently dropped
      // those classes and both components rendered with no background.
      colors: {
        card: "#0f172a", // slate-900, matches the dashboard panels
        "muted-foreground": "#94a3b8", // slate-400
      },
    },
  },
  plugins: [],
};
