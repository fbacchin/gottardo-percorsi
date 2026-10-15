// Prove della pagina. Uso: node sito/prova_sito.mjs
import assert from "node:assert/strict";
import { mappaValida, momenti, quanto } from "./logica.mjs";

assert.ok(mappaValida("2026-10-15-1800-apple.svg"));
for (const cattivo of ["../README.md", "2026-10-15-1800-apple.svg/../../uso.json", "dati/apple-2026-10.csv", "2026-10-15-1800-altro.svg"])
  assert.ok(!mappaValida(cattivo), cattivo);

const m = momenti(["2026-10-15-1745-apple.svg", "2026-10-15-1800-tomtom.svg", "2026-10-15-1800-apple.svg", "appunti.txt"]);
assert.deepEqual(m.map((x) => x.quando), ["2026-10-15 18:00", "2026-10-15 17:45"]);
assert.deepEqual(m[0].file, { apple: "2026-10-15-1800-apple.svg", tomtom: "2026-10-15-1800-tomtom.svg" });

assert.deepEqual([0, 1, 3, 4, 6, 11].map(quanto), ["adesso", "15 minuti fa", "45 minuti fa", "1 h fa", "1 h 30 min fa", "2 h 45 min fa"]);
console.log("prove della pagina: ok");
