// Keys must match backend/candidates.py's INTEREST_PLACE_TYPES.
export const INTEREST_OPTIONS = [
  { key: "nature", label: "Nature" },
  { key: "culture", label: "Culture & History" },
  { key: "spiritual", label: "Spiritual" },
  { key: "recreation", label: "Recreation" },
  { key: "culinary", label: "Culinary" },
  { key: "business", label: "Business" },
];

// Keys must match backend/llm.py's LOCALE_TONE_INSTRUCTIONS -- except
// "others", which has no entry there on purpose: llm.py's
// _locale_instruction() already falls back to no tone override for any
// unrecognized key, so "others" (for non-SEA users) needs no backend
// change at all.
export const LOCALE_OPTIONS = [
  { key: "", label: "Neutral (default)" },
  { key: "indonesian", label: "Indonesian" },
  { key: "malaysian", label: "Malaysian" },
  { key: "singaporean", label: "Singaporean" },
  { key: "filipino", label: "Filipino" },
  { key: "thai", label: "Thai" },
  { key: "vietnamese", label: "Vietnamese" },
  { key: "others", label: "Others (not listed)" },
];
