import type { Config } from "tailwindcss";

// Colors mirror docs/project.md §6-7 exactly — do not add new colors here
// without updating that spec first. See docs/claude.md, "Design system rules".
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "#050505",
          secondary: "#0A0A0A",
        },
        card: {
          DEFAULT: "#111111",
          elevated: "#171717",
        },
        border: {
          DEFAULT: "#222222",
          divider: "#2E2E2E",
        },
        text: {
          secondary: "#666666",
          muted: "#999999",
          body: "#D4D4D4",
          primary: "#F5F5F5",
          max: "#FFFFFF",
        },
        success: "#22C55E",
        warning: "#F59E0B",
        danger: "#EF4444",
        info: "#3B82F6",
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
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
      borderRadius: {
        DEFAULT: "6px",
        lg: "8px",
      },
      spacing: {
        4.5: "18px",
      },
    },
  },
  plugins: [],
};

export default config;
