// Storyfolk build: one command that rebuilds all of the site's art. It runs every generator in
// tools/, then bakes the ink and halo filters of every assets/*.svg into plain geometry with
// tools/bake.mjs, which is what lets the drawings render and animate without runtime filters.
//
// usage: node tools/build.mjs            (from any directory)
//
// The generators run from the repository root with the environment passed through: python3 for
// the .py ones, node for the .mjs ones, the hero letters first (the cast sits on them). Two of
// them import shapely, so python3 must be able to import it: pip install shapely, or put it on
// PYTHONPATH. A drawing without filters (the logo) is left as it is by the bake.

import { spawnSync } from "node:child_process";
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { bakeSvg } from "./bake.mjs";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const TOOLS = path.join(ROOT, "tools");
const ASSETS = path.join(ROOT, "assets");
const FIRST = ["generate-hero-letters.py"];

// ------------------------------------------------------------------ generators

const generators = readdirSync(TOOLS)
	.filter((f) => /^generate-.*\.(py|mjs)$/.test(f))
	.sort((a, b) => FIRST.includes(b) - FIRST.includes(a) || a.localeCompare(b));
const interpreter = (file) => (file.endsWith(".py") ? "python3" : process.execPath);
const run = (cmd, args) => spawnSync(cmd, args, { cwd: ROOT, env: process.env, stdio: "inherit" });

// Check the Python side before regenerating anything, so a missing module never leaves the
// art half rebuilt.
const python = generators.filter((f) => f.endsWith(".py"));
const shapely = python.filter((f) =>
	/^\s*(import|from)\s+shapely\b/m.test(readFileSync(path.join(TOOLS, f), "utf8")),
);
if (python.length && spawnSync("python3", ["--version"], { env: process.env }).status !== 0) {
	console.error(
		"build: python3 is not on PATH, and these generators need it:\n  " + python.join("\n  "),
	);
	process.exit(1);
}
if (
	shapely.length &&
	spawnSync("python3", ["-c", "import shapely"], { env: process.env }).status !== 0
) {
	console.error(
		`build: python3 cannot import shapely, which ${shapely.join(" and ")} need.\n` +
			"  Install it (pip install shapely) or point PYTHONPATH at a copy, then run again.",
	);
	process.exit(1);
}

let failed = 0;
for (const file of generators) {
	const started = Date.now();
	console.log(`build: ${interpreter(file) === "python3" ? "python3" : "node"} tools/${file}`);
	const result = run(interpreter(file), [path.join("tools", file)]);
	if (result.status !== 0) {
		console.error(
			`build: tools/${file} failed (${result.error?.message ?? `exit code ${result.status}`})`,
		);
		failed++;
		break;
	}
	console.log(`       done in ${((Date.now() - started) / 1000).toFixed(1)} s`);
}

// ------------------------------------------------------------------ bake

// Bake even after a failed generator: whatever is in assets/ then still draws without filters.
let before = 0;
let after = 0;
let broken = 0;
const svgs = readdirSync(ASSETS).filter((f) => f.endsWith(".svg"));
for (const file of svgs.sort()) {
	const target = path.join(ASSETS, file);
	const src = readFileSync(target, "utf8");
	let result;
	try {
		result = bakeSvg(src);
	} catch (e) {
		console.error(`bake: assets/${file} was not baked: ${e.message}`);
		broken++;
		continue;
	}
	const { svg, notes } = result;
	before += Buffer.byteLength(src);
	after += Buffer.byteLength(svg);
	if (svg !== src) writeFileSync(target, svg);
	const kb = (s) => `${(Buffer.byteLength(s) / 1024).toFixed(1)} KB`;
	console.log(`bake: assets/${file}: ${svg === src ? "unchanged" : `${kb(src)} -> ${kb(svg)}`}`);
	for (const note of notes.slice(svg === src ? 1 : 0)) console.log(`  ${note}`);
}
console.log(`bake: ${(before / 1024).toFixed(0)} KB -> ${(after / 1024).toFixed(0)} KB in all`);
if (failed) console.error("build: a generator failed, so some drawings were not regenerated");
if (broken) console.error("build: some drawings could not be baked (see above)");
if (failed || broken) process.exit(1);
