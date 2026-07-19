// Keys must match backend/candidates.py's INTEREST_PLACE_TYPES.
export const INTEREST_OPTIONS = [
  { key: "nature", label: "Nature" },
  { key: "culture", label: "Culture & History" },
  { key: "spiritual", label: "Spiritual" },
  { key: "recreation", label: "Recreation" },
  { key: "culinary", label: "Culinary" },
  { key: "business", label: "Business" },
];

// Keys must match backend/llm.py's LOCALE_TONE_INSTRUCTIONS.
// Tone/phrasing only -- never affects which places are picked.
export const LOCALE_OPTIONS = [
  { key: "", label: "Neutral (default)" },
  { key: "indonesian", label: "Indonesian" },
  { key: "malaysian", label: "Malaysian" },
  { key: "singaporean", label: "Singaporean" },
  { key: "filipino", label: "Filipino" },
  { key: "thai", label: "Thai" },
  { key: "vietnamese", label: "Vietnamese" },
];
