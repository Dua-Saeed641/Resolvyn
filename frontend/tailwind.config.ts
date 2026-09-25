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
        brand: { DEFAULT: v("brand"), foreground: v("brand-foreground") },
        success: v("success"),
        warning: v("warning"),
        danger: v("danger"),
        info: v("info"),
        // Categorical chart palette (analytics dashboard only) — fixed slot order maps
        // 1:1 to lib/constants.ts's DEPARTMENTS, dark-mode steps from the dataviz skill's
        // validated default (references/palette.md), re-checked with its colorblind-safety
        // validator for this 5-slot subset. Never reorder or reassign a slot's department.
        chart: {
          1: "#3987e5", // Technical
          2: "#d95926", // Billing
          3: "#199e70", // Account
          4: "#c98500", // Order
          5: "#d55181", // Other
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        display: ["var(--font-display)", "var(--font-sans)", "system-ui", "sans-serif"],
      },
      borderRadius: { lg: "var(--radius)", md: "calc(var(--radius) - 2px)", sm: "calc(var(--radius) - 4px)", DEFAULT: "6px" },
      spacing: { 4.5: "18px" },
      boxShadow: {
        card: "0 1px 2px 0 hsl(0 0% 0% / 0.04)",
        float: "0 12px 32px -12px hsl(0 0% 0% / 0.18), 0 2px 6px -2px hsl(0 0% 0% / 0.06)",
        glow: "0 0 0 1px hsl(var(--brand) / 0.25), 0 8px 28px -8px hsl(var(--brand) / 0.45)",
      },
      animation: { float: "float 7s ease-in-out infinite", drift: "drift 18s ease-in-out infinite", eq: "eq 1s ease-in-out infinite" },
      keyframes: {
        float: { "0%, 100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-8px)" } },
        drift: { "0%, 100%": { transform: "translate3d(0,0,0) scale(1)" }, "50%": { transform: "translate3d(2%,-3%,0) scale(1.06)" } },
        eq: { "0%, 100%": { transform: "scaleY(0.3)" }, "50%": { transform: "scaleY(1)" } },
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
      },
    },
  },
  plugins: [animate],
};

export default config;
