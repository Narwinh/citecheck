// Copy a committed eval run into frontend/data/eval.json for the /eval page.
// Runs before `next build`. If ../eval is not available (e.g. a deploy that
// only contains frontend/), the committed data/eval.json is used unchanged.
//
//   EVAL_RUN=v1 node scripts/sync-eval.mjs

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const run = process.env.EVAL_RUN ?? "v1";
const src = join(here, "..", "..", "eval", "results", run);
const out = join(here, "..", "data", "eval.json");

if (!existsSync(join(src, "summary.json"))) {
  console.log(`sync-eval: ${src} not found; keeping existing data/eval.json`);
  process.exit(0);
}

const read = (name) => JSON.parse(readFileSync(join(src, name), "utf8"));
const data = { run, summary: read("summary.json"), config: read("config.json") };
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify(data, null, 1) + "\n");
console.log(`sync-eval: wrote data/eval.json from eval/results/${run}`);
