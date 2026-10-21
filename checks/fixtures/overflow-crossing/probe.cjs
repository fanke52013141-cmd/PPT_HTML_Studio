"use strict";
// Replay frozen overflow/crossing measurements through the original detection
// cores. No browser, provider or author write: capacity.cjs and
// vector-overlap.cjs are the production predicates themselves.
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "../../..");
const { capacityEvidence } = require(path.join(root, "html_engine/visual/capacity.cjs"));
const vectorOverlap = require(path.join(root, "html_engine/tools/vector-overlap.cjs"));

const dataset = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const results = [];
for (const testCase of dataset.cases) {
  const started = process.hrtime.bigint();
  let verdict;
  if (testCase.kind === "text_overflow") {
    const evidence = capacityEvidence(testCase.measured, testCase.limits);
    verdict = { flagged: evidence.triggers.length > 0, triggers: evidence.triggers };
  } else {
    const pairResults = testCase.pairs.map(([a, b]) =>
      vectorOverlap.vectorPair(testCase.frame, a, b, testCase.nodes),
    );
    const overlap = pairResults.some((result) => result && result.overlap);
    const undetermined = !overlap && pairResults.some((result) => result === null);
    verdict = { flagged: overlap, undetermined, pairs: pairResults };
  }
  const elapsedMs = Number(process.hrtime.bigint() - started) / 1e6;
  results.push({ id: testCase.id, kind: testCase.kind, verdict, elapsed_ms: elapsedMs });
}
process.stdout.write(
  JSON.stringify({ version: vectorOverlap.VERSION, results }),
);
