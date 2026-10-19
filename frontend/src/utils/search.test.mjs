import test from "node:test";
import assert from "node:assert/strict";
import { matchesSearch, normalizeSearch, searchRecords } from "./search.mjs";

test("multiple words can match different fields, irrespective of case or order", () => {
  assert.equal(matchesSearch("ALICE electronics", "Bluetooth speaker", "Electronics", "Alice"), true);
  assert.equal(matchesSearch("electronics alice", "Bluetooth speaker", "Electronics", "Alice"), true);
  assert.equal(matchesSearch("alice books", "Bluetooth speaker", "Electronics", "Alice"), false);
});

test("student IDs, email addresses, accents and punctuation remain searchable", () => {
  assert.equal(matchesSearch("S11192806@STUDENT.USP.AC.FJ", "s11192806@student.usp.ac.fj"), true);
  assert.equal(matchesSearch("cafe table", "Café-table"), true);
  assert.equal(matchesSearch("#52", 52, null, undefined), true);
  assert.equal(matchesSearch("under review", "under_review"), true);
  assert.equal(normalizeSearch("  Study   Supplies "), "study supplies");
});

test("exact and title matches rank first without changing the stored records", () => {
  const records = [{ id: 1, name: "Cupboard", category: "Books" }, { id: 2, name: "Books", category: "Study" }, { id: 3, name: "Bookshelf", category: "Furniture" }];
  const result = searchRecords(records, "books", (record) => [record.name, record.category]);
  assert.deepEqual(result.map((record) => record.id), [2, 1, 3]);
  assert.deepEqual(records.map((record) => record.id), [1, 2, 3]);
  assert.equal(searchRecords(records, "", (record) => [record.name]), records);
  assert.deepEqual(searchRecords(records, "no such item", (record) => [record.name]), []);
});

test("search treats special characters as text rather than executing a pattern", () => {
  assert.equal(matchesSearch("book.*", "Book"), true);
  assert.equal(matchesSearch("[invalid regex", "Books"), false);
});
