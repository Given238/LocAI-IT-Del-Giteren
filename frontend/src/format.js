export function formatIdr(amount) {
  return `Rp${Math.round(amount).toLocaleString("id-ID")}`;
}

export function formatPriceRange(min, max) {
  if (min == null && max == null) return "Price not available";
  if (min === 0 && max === 0) return "Free";
  if (min === max) return formatIdr(min);
  return `${formatIdr(min)} – ${formatIdr(max)}`;
}
