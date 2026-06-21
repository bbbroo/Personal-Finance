/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(180 8% 86%)",
        input: "hsl(180 8% 86%)",
        ring: "hsl(173 80% 32%)",
        background: "hsl(160 20% 98%)",
        foreground: "hsl(180 10% 12%)",
        primary: {
          DEFAULT: "hsl(173 80% 30%)",
          foreground: "hsl(0 0% 100%)"
        },
        muted: {
          DEFAULT: "hsl(160 12% 93%)",
          foreground: "hsl(170 7% 35%)"
        },
        card: {
          DEFAULT: "hsl(0 0% 100%)",
          foreground: "hsl(180 10% 12%)"
        },
        warning: {
          DEFAULT: "hsl(45 90% 45%)",
          foreground: "hsl(45 30% 15%)"
        },
        danger: {
          DEFAULT: "hsl(0 70% 46%)",
          foreground: "hsl(0 0% 100%)"
        }
      },
      borderRadius: {
        lg: "8px",
        md: "6px",
        sm: "4px"
      },
      boxShadow: {
        soft: "0 8px 24px rgba(22, 40, 38, 0.08)"
      }
    }
  },
  plugins: []
};
