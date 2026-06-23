import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        line: "var(--border)",
        text: "var(--text)",
        muted: "var(--text-muted)",
        faint: "var(--text-faint)",
        primary: "var(--primary)",
        info: "var(--info)",
        accent: "var(--accent)",
        violet: "var(--violet)",
        danger: "var(--danger)",
      },
    },
  },
  plugins: [],
};
export default config;
