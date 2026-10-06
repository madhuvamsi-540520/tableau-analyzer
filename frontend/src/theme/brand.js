// Mastech ADEPT brand theme — single source of truth.
// Ported verbatim from "Mastech Agentic Platform — Brand Theme.html".
// Mirrored as CSS custom properties in styles.css for CSS-only rules.
// Components that need a literal (non-CSS-var) value — e.g. AntD
// ConfigProvider tokens, which run their own color math — read BRAND /
// BRAND_DARK directly. Plain inline styles should prefer the CSS vars
// (var(--accent), var(--text-primary), ...) so they stay theme-reactive
// without prop drilling.
export const BRAND = {
  // Brand colors — illustration, gradients and brand marks ONLY.
  // Never used as body text/small labels (light-mode green fails contrast).
  tealPrimary: "#0F6D6B",
  tealDeep: "#0F504E",
  ink: "#0A3645",
  green: "#06E478",
  greenBright: "#00EF7B",
  white: "#FFFFFF",
  surfaceLight: "#F3F6F7",
  borderBrand: "#C6C6C6",

  // Semantic tokens — light theme (default export values)
  bg: "#FFFFFF",
  surface: "#F3F6F7",
  surfaceAlt: "#E8EDEE",
  border: "#C6C6C6",
  textPrimary: "#0A3645",
  textSecondary: "#4A6A72",
  accent: "#0F6D6B",
  accentHover: "#0F504E",
  onAccent: "#FFFFFF",
  focusRing: "#0F6D6B",

  success: "#06E478",
  error: "#D93025",
  warning: "#E97132",
  info: "#0F9ED5",

  fontHead: '"Space Grotesk", ui-sans-serif, system-ui, sans-serif',
  fontBody: '"Inter", ui-sans-serif, system-ui, sans-serif',

  radiusSm: 6,
  radiusMd: 10,
  radiusLg: 16,
};

// Dark-theme overrides for the semantic tokens only — brand colors and
// fonts are theme-independent, so BRAND_DARK is meant to be spread on
// top of BRAND: { ...BRAND, ...BRAND_DARK }.
export const BRAND_DARK = {
  bg: "#0A3645",
  surface: "#0F504E",
  surfaceAlt: "#0F6D6B",
  border: "#1E5F62",
  textPrimary: "#FFFFFF",
  textSecondary: "#BFD6D5",
  accent: "#06E478",
  accentHover: "#00EF7B",
  onAccent: "#062B2A",
  focusRing: "#06E478",
};

export function brandTokens(dark) {
  return dark ? { ...BRAND, ...BRAND_DARK } : BRAND;
}
