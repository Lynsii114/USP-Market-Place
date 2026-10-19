import test from "node:test";
import assert from "node:assert/strict";
import { canonicalCategoryName, mergeCategoryOptions } from "./categories.mjs";

const defaults = [{ id: "builtin-1", name: "Books", image: "books.jpg" }, { id: "builtin-5", name: "Footwear", image: "shoes.jpg" }, { id: "builtin-9", name: "Other", image: "other.jpg" }];

test("legacy footwear spelling maps to the current category", () => {
  assert.equal(canonicalCategoryName(" Footwares "), "Footwear");
  assert.equal(canonicalCategoryName("FOOTWEAR"), "Footwear");
});

test("database defaults do not replace stock photos or create duplicate options", () => {
  const options = mergeCategoryOptions(defaults, [{ id: 5, name: "Footwares", image: null }, { id: 1, name: "books" }]);
  assert.equal(options.length, 3);
  assert.equal(options.find((option) => option.name === "Footwear").image, "shoes.jpg");
});

test("custom categories remain available before Other without ID collisions", () => {
  const options = mergeCategoryOptions(defaults, [{ id: 1, name: "Accessories", created_at: "2026-10-18" }]);
  assert.equal(options.at(-1).name, "Other");
  assert.equal(options.find((option) => option.name === "Accessories").id, 1);
  assert.equal(new Set(options.map((option) => option.id)).size, options.length);
});
