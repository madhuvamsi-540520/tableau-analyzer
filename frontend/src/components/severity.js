import { BRAND } from "../theme/brand.js";

// ADEPT brand rule: sequential/graded data uses the teal -> green ramp,
// never a rainbow scale. Discrete severity still needs a visually alarming
// top end, so critical/high use the semantic error/warning tokens instead.
export const SEVERITY_COLOR = {
  critical: BRAND.error,
  high: BRAND.warning,
  medium: BRAND.warning,
  low: BRAND.info,
  info: BRAND.info,
};

export const SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };

// Worst -> best, walking the brand's own teal -> green sequential ramp.
const SCORE_RAMP = [BRAND.ink, BRAND.tealDeep, BRAND.tealPrimary, BRAND.green, BRAND.greenBright];

export function bandColor(band = "") {
  if (band.startsWith("Excellent")) return SCORE_RAMP[4];
  if (band === "Good") return SCORE_RAMP[3];
  if (band === "Moderate") return SCORE_RAMP[2];
  if (band === "Developing") return SCORE_RAMP[1];
  return SCORE_RAMP[0];
}

export function scoreColor(score) {
  if (score >= 85) return SCORE_RAMP[4];
  if (score >= 70) return SCORE_RAMP[3];
  if (score >= 55) return SCORE_RAMP[2];
  if (score >= 40) return SCORE_RAMP[1];
  return SCORE_RAMP[0];
}

// A-F letter grades, worst (F) to best (A), same ramp as scoreColor/bandColor.
const GRADE_RAMP = [BRAND.ink, BRAND.tealDeep, BRAND.tealPrimary, "#0AA972", BRAND.green, BRAND.greenBright];
const GRADE_ORDER = ["F", "E", "D", "C", "B", "A"];

export function gradeColor(grade) {
  const i = GRADE_ORDER.indexOf(grade);
  return i === -1 ? BRAND.textSecondary : GRADE_RAMP[i];
}
