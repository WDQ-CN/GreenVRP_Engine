import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        ink: {
          DEFAULT: "hsl(var(--ink))",
          soft: "hsl(var(--ink-soft))",
        },
        forest: "hsl(var(--forest))",
        moss: "hsl(var(--moss))",
        lime: {
          DEFAULT: "hsl(var(--lime))",
          deep: "hsl(var(--lime-deep))",
        },
        paper: "hsl(var(--paper))",
        cream: "hsl(var(--cream))",
        sand: "hsl(var(--sand))",
        mint: "hsl(var(--mint))",
        amber: "hsl(var(--amber))",
        sky: "hsl(var(--sky))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
      },
      fontFamily: {
        sans: ["Inter", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", "sans-serif"],
        serif: ["Instrument Serif", "Noto Serif SC", "Songti SC", "SimSun", "serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 4px)",
        sm: "calc(var(--radius) - 8px)",
      },
      boxShadow: {
        soft: "0 18px 40px -24px hsl(var(--ink) / 0.35)",
        lift: "0 30px 80px -32px hsl(var(--ink) / 0.45)",
        glow: "0 0 0 1px hsl(var(--lime) / 0.25), 0 24px 80px -28px hsl(var(--lime) / 0.35)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        rise: {
          "0%": { opacity: "0", transform: "translateY(28px)", filter: "blur(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)", filter: "blur(0)" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-12px)" },
        },
        drift: {
          "0%": { transform: "translate3d(-2%, 0, 0)" },
          "50%": { transform: "translate3d(2%, -1.5%, 0)" },
          "100%": { transform: "translate3d(-2%, 0, 0)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "0.55", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.06)" },
        },
        flow: {
          to: { strokeDashoffset: "-64" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.25" },
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
        "draw-line": {
          to: { strokeDashoffset: "0" },
        },
        "spin-slow": {
          to: { transform: "rotate(360deg)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        rise: "rise 0.9s cubic-bezier(0.16, 1, 0.3, 1) both",
        marquee: "marquee 38s linear infinite",
        float: "float 7s ease-in-out infinite",
        drift: "drift 26s ease-in-out infinite",
        "pulse-soft": "pulse-soft 4.5s ease-in-out infinite",
        flow: "flow 2.4s linear infinite",
        blink: "blink 2s ease-in-out infinite",
        shimmer: "shimmer 2.2s linear infinite",
        "spin-slow": "spin-slow 46s linear infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}

export default config
