// Mirrors app/backend/publishing/channel_profiles.py: which channels the app can publish to itself.
export const CHANNEL_TYPES = [
  { value: "etsy", label: "Etsy", mode: "api" },
  { value: "shopify", label: "Shopify", mode: "api" },
  { value: "bol", label: "bol", mode: "api" },
  { value: "marktplaats", label: "Marktplaats", mode: "hulpmodus" },
  { value: "vinted", label: "Vinted", mode: "hulpmodus" },
  { value: "overig", label: "Overig kanaal", mode: "hulpmodus" },
] as const;

const API_TYPES = new Set<string>(CHANNEL_TYPES.filter((item) => item.mode === "api").map((item) => item.value));

export function isAssistedType(type?: string | null) {
  return !API_TYPES.has((type || "").trim().toLowerCase());
}
