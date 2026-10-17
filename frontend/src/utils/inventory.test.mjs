import test from "node:test";
import assert from "node:assert/strict";
import { priceRange, matchesPrice, inventorySummary, sellerListingStatus } from "./inventory.mjs";

test("price filters include boundary prices and allow open ends", () => {
  assert.equal(matchesPrice(12.5, priceRange("12.50", "12.50")), true);
  assert.equal(matchesPrice(12.49, priceRange("12.50", "")), false);
  assert.equal(matchesPrice(12.51, priceRange("", "12.50")), false);
  assert.equal(matchesPrice(35, priceRange("", "")), true);
});

test("invalid ranges give an error instead of silently showing unrelated results", () => {
  for (const values of [["20", "10"], ["-1", ""], ["", "Infinity"], ["abc", "10"]]) {
    const range = priceRange(...values);
    assert.ok(range.error);
    assert.equal(matchesPrice(15, range), false);
  }
});

test("numeric prices are compared as amounts rather than strings", () => {
  assert.equal(matchesPrice("100", priceRange("20", "90")), false);
  assert.equal(matchesPrice("35.00", priceRange("30", "40")), true);
});

test("available-unit totals exclude reserved, sold and inactive stock", () => {
  assert.deepEqual(inventorySummary([
    { status: "available", stock: 5 }, { status: "available", stock: 2 },
    { status: "reserved", stock: 3 }, { status: "sold", stock: 0 },
    { status: "hidden", stock: 4 }, { status: "hidden", stock: 2, admin_restricted: true },
  ]), { total: 6, available: 2, reserved: 1, sold: 1, inactive: 2, units: 7 });
});

test("empty inventories show zeros and inconsistent zero stock is treated as sold", () => {
  assert.deepEqual(inventorySummary([]), { total: 0, available: 0, reserved: 0, sold: 0, inactive: 0, units: 0 });
  assert.equal(sellerListingStatus({ status: "available", stock: 0 }), "sold");
  assert.equal(sellerListingStatus({ status: "hidden", stock: 0 }), "inactive");
});
