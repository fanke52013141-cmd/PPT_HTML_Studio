"use strict";
const path = require("path"),
  esbuild = require("esbuild");
esbuild
  .build({
    entryPoints: [path.join(__dirname, "sample.cjs")],
    bundle: true,
    platform: "browser",
    outfile: path.join(__dirname, "sample.js"),
    minify: true,
    legalComments: "none",
  })
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  });
