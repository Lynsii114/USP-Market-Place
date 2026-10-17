export function canonicalCategoryName(value) {
  const name = String(value || "").trim();
  return ["footwares", "footwear"].includes(name.toLowerCase()) ? "Footwear" : name;
}

export function mergeCategoryOptions(defaults, stored) {
  const merged = [...defaults];
  for (const category of stored) {
    const name = canonicalCategoryName(category.name);
    if (!merged.some((existing) => existing.name.toLowerCase() === name.toLowerCase())) {
      merged.push({ ...category, name });
    }
  }
  return [...merged.filter((category) => category.name !== "Other"), ...merged.filter((category) => category.name === "Other")];
}
