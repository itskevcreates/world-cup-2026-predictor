import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b1020",
        card: "#151c33",
        accent: "#22d3a6",
        muted: "#8aa0c8",
      },
    },
  },
  plugins: [],
};
export default config;
