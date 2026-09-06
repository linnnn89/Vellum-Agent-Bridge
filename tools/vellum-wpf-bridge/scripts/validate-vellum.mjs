/**
 * Canonical .vellum validation using Vellum's DocumentModel.parse().
 * Node is a test-time dependency only; the runtime bridge stays pure Python.
 *
 * Usage:
 *   node tools/vellum-wpf-bridge/scripts/validate-vellum.mjs <file.vellum> [...]
 */
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const documentJs = resolve(here, "../../../src/document.js");
const { DocumentModel } = await import(pathToFileURL(documentJs).href);

const files = process.argv.slice(2);
if (!files.length) {
  console.error("Usage: node validate-vellum.mjs <file.vellum> [...]");
  process.exit(2);
}

let failed = 0;
for (const file of files) {
  const abs = resolve(file);
  try {
    const text = readFileSync(abs, "utf8");
    const parsed = DocumentModel.parse(text);
    const roundTrip = DocumentModel.parse(JSON.stringify(parsed));
    if (!roundTrip.pages?.length) {
      throw new Error("round-trip parse produced no pages");
    }
    console.log(`PASS ${abs}`);
  } catch (err) {
    failed += 1;
    console.error(`FAIL ${abs}: ${err.message || err}`);
  }
}
process.exit(failed ? 1 : 0);
