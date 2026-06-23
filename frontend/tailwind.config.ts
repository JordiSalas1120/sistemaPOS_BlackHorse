import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#fdf8f0",
          100: "#faecd9",
          200: "#f4d5a8",
          300: "#ecb96d",
          400: "#e49840",
          500: "#d97f22",  // cuero
          600: "#c4661a",
          700: "#a35018",
          800: "#84401b",
          900: "#6c3619",
        },
      },
    },
  },
  plugins: [],
};

export default config;
