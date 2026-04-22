import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      boxShadow: {
        soft: "0 8px 24px rgba(15, 23, 42, 0.08)",
      },
      colors: {
        bg: "#f7f8fb",
      },
    },
  },
  plugins: [],
};

export default config;
