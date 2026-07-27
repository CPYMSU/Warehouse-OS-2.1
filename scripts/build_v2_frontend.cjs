#!/usr/bin/env node
"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const V2 = path.join(ROOT, "frontend", "v2");
const Babel = require(path.join(V2, "vendor", "babel.min.js"));

const TARGETS = Object.freeze({
  "app.bundle.js": "index.html",
  "personal.bundle.js": "personal.html",
});

function manifestSources(entryName) {
  const html = fs.readFileSync(path.join(V2, entryName), "utf8");
  const template = html.match(
    /<template\s+id=["']w2-precompile-sources["'][^>]*>([\s\S]*?)<\/template>/i
  );
  if (!template) throw new Error(`missing w2-precompile-sources manifest in ${entryName}`);
  const files = [];
  const seen = new Set();
  const script = /<script\s+type=["']application\/x-warehouse-source["']\s+src=["']([^"']+)["'][^>]*><\/script>/gi;
  for (let match = script.exec(template[1]); match; match = script.exec(template[1])) {
    const relative = match[1].split("?", 1)[0];
    if (!relative || relative.startsWith("/") || relative.includes("\\") || relative.split("/").includes("..")) {
      throw new Error(`unsafe V2 bundle source in ${entryName}: ${relative}`);
    }
    if (seen.has(relative)) throw new Error(`duplicate V2 bundle source in ${entryName}: ${relative}`);
    seen.add(relative);
    files.push(relative);
  }
  if (!files.length) throw new Error(`empty V2 bundle source manifest in ${entryName}`);
  return files;
}

function sourceFor(files) {
  return files.map((relative) => {
    const absolute = path.join(V2, relative);
    if (!fs.existsSync(absolute)) {
      throw new Error(`missing V2 bundle source: ${relative}`);
    }
    return `/* SOURCE: ${relative} */\n${fs.readFileSync(absolute, "utf8")}`;
  }).join("\n;\n");
}

function buildTarget(outputName, files) {
  const source = sourceFor(files);
  const digest = crypto.createHash("sha256").update(source).digest("hex");
  const transformed = Babel.transform(source, {
    presets: [
      ["env", {
        targets: { chrome: "100", firefox: "100", safari: "15" },
        bugfixes: true,
      }],
      "react",
    ],
    sourceType: "script",
    compact: true,
    minified: true,
    comments: false,
    filename: outputName.replace(/\.js$/, ".jsx"),
  }).code;
  return `/* WAREHOUSE OS 2.0 · PRECOMPILED · sources-sha256:${digest} */\n${transformed}\n`;
}

function main() {
  const check = process.argv.includes("--check");
  const outputDir = path.join(V2, "dist");
  const results = [];
  if (!check) fs.mkdirSync(outputDir, { recursive: true });

  for (const [outputName, entryName] of Object.entries(TARGETS)) {
    const files = manifestSources(entryName);
    const output = buildTarget(outputName, files);
    const destination = path.join(outputDir, outputName);
    if (check) {
      if (!fs.existsSync(destination)) {
        throw new Error(`missing precompiled V2 bundle: ${path.relative(ROOT, destination)}`);
      }
      const current = fs.readFileSync(destination, "utf8");
      if (current !== output) {
        throw new Error(`stale precompiled V2 bundle: ${path.relative(ROOT, destination)}; run node scripts/build_v2_frontend.cjs`);
      }
    } else {
      fs.writeFileSync(destination, output, "utf8");
    }
    results.push(`${outputName} ${Buffer.byteLength(output)} bytes`);
  }
  process.stdout.write(`${check ? "verified" : "built"}: ${results.join(", ")}\n`);
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
}
