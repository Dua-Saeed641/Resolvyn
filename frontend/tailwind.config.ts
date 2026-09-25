import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

// Colours are CSS variables (app/globals.css) so light and dark share one set of classes.
// The legacy token names (bg-card, text-text-primary, border-border, text-success...) map onto the same palette,
// so every screen follows the theme. Palette: neutral zinc plus four muted status colours. No neon, no gradients.
const v = (name: string) => `hsl(var(--${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./features/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // shadcn/ui
        background: v("background"),
        foreground: v("foreground"),
        primary: { DEFAULT: v("primary"), foreground: v("primary-foreground") },
        secondary: { DEFAULT: v("secondary"), foreground: v("secondary-foreground") },
        muted: { DEFAULT: v("muted"), foreground: v("muted-foreground") },
        accent: { DEFAULT: v("accent"), foreground: v("accent-foreground") },
        destructive: { DEFAULT: v("destructive"), foreground: v("destructive-foreground") },
        popover: { DEFAULT: v("popover"), foreground: v("popover-foreground") },
        input: v("input"),
        ring: v("ring"),
        card: { DEFAULT: v("card"), foreground: v("card-foreground"), elevated: v("card-elevated") },
        border: { DEFAULT: v("border"), divider: v("divider") },
        // legacy tokens
        bg: { primary: v("background"), secondary: v("bg-secondary") },
        text: {
          secondary: v("text-secondary"),
          muted: v("text-muted"),
          body: v("text-body"),
          primary: v("text-primary"),
          max: v("text-max"),
        },
        success: v("success"),
        warning: v("warning"),
        danger: v("danger"),
        info: v("info"),
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      borderRadius: { lg: "var(--radius)", md: "calc(var(--radius) - 2px)", sm: "calc(var(--radius) - 4px)", DEFAULT: "6px" },
      spacing: { 4.5: "18px" },
      boxShadow: { card: "0 1px 2px 0 hsl(240 6% 10% / 0.04)" },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
      },
    },
  },
  plugins: [animate],
};

export default config;
