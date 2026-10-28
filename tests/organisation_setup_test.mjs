import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

// Import the same ES module that webpack compiles, without adding runtime dependencies.
const source = await readFile(new URL("../app/app/packs/src/organisation_setup/form.js", import.meta.url), "utf8");
const { suggestShortName, suggestPrefix } = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

test("short names retain short names and prefer initials or whole words", () => {
  assert.equal(suggestShortName("  Our   Group "), "Our Group");
  assert.equal(suggestShortName("Neighbourhood Climate Assembly"), "NCA");
  assert.equal(suggestShortName("Community Assembly"), "Community");
  assert.equal(suggestShortName("Supercalifragilistic"), "Supercalifra");
  assert.equal(suggestShortName(""), "");
  assert.equal(suggestShortName("AB"), "AB"); // Do not invent padding to satisfy validation.
});

test("prefixes use word initials, including two-word and single-word names", () => {
  assert.equal(suggestPrefix("Riverside Community Garden"), "RCG");
  assert.equal(suggestPrefix("Riverbank Gardeners"), "RG");
  assert.equal(suggestPrefix("Café"), "C");
  assert.equal(suggestPrefix("École Communale"), "EC");
  assert.equal(suggestPrefix("  Riverbank-Gardeners & Neighbours  "), "RGN");
  assert.equal(suggestPrefix("a ".repeat(14)), "A".repeat(14));
  assert.equal(suggestPrefix("Asamblea de Ñuñoa"), "ADN");
  assert.equal(suggestPrefix("Neighbourhood Climate Assembly"), "NCA");
  assert.equal(suggestPrefix("共同体"), "共");
  assert.equal(suggestPrefix("  !!  "), "");
  assert.equal(suggestPrefix(""), "");
});

test("short names respect their 12-character limit, including Unicode", () => {
  for (const name of ["a ".repeat(40), "🌱".repeat(20), "é".repeat(30), "自治".repeat(15), "Straße".repeat(10)]) {
    assert.ok(Array.from(suggestShortName(name)).length <= 12);
  }
});
