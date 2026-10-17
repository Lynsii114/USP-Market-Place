export function priceRange(minimum, maximum) {
  const min = String(minimum).trim() === "" ? null : Number(minimum);
  const max = String(maximum).trim() === "" ? null : Number(maximum);
  if ((min !== null && (!Number.isFinite(min) || min < 0)) || (max !== null && (!Number.isFinite(max) || max < 0))) {
    return { min, max, error: "Enter a price of 0 or more." };
  }
  if (min !== null && max !== null && min > max) return { min, max, error: "Minimum price must not exceed maximum price." };
  return { min, max, error: "" };
}

export function matchesPrice(price, range) {
  return !range.error && (range.min === null || Number(price) >= range.min) && (range.max === null || Number(price) <= range.max);
}

export function sellerListingStatus(listing) {
  if (listing.status === "hidden" || listing.status === "removed") return "inactive";
  if (listing.status === "sold" || Number(listing.stock) <= 0) return "sold";
  return listing.status === "reserved" ? "reserved" : "available";
}

export function inventorySummary(listings) {
  const summary = { total: listings.length, available: 0, reserved: 0, sold: 0, inactive: 0, units: 0 };
  for (const listing of listings) {
    const status = sellerListingStatus(listing);
    summary[status] += 1;
    if (status === "available") summary.units += Math.max(0, Number(listing.stock) || 0);
  }
  return summary;
}
