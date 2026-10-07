"use strict";
const fs = require("fs"),
  path = require("path");
const { compileRecipe } = require("../src/recipes.cjs");
const root = path.resolve(__dirname, "..");
// Validate every input before touching previous valid derived scenes.
const planned = [
  "course-water",
  "course-everyday",
  "e2-cloud",
  "token-01",
  "token-02",
  "token-03",
  "token-04",
  "token-05",
].map((name) => {
  const input = JSON.parse(
    fs.readFileSync(path.join(root, "recipes", name + ".recipe.json"), "utf8"),
  );
  return { name, result: compileRecipe(input) };
});
const manifest = JSON.parse(
  fs.readFileSync(path.join(root, "courses/token/course.json"), "utf8"),
);
const course = {
  ...manifest,
  scenes: manifest.scenes.map(({ recipe }) => {
    const entry = planned.find((p) => p.name === recipe);
    if (!entry) throw new Error("COURSE_RECIPE_MISSING " + recipe);
    return {
      id: entry.result.scene.id,
      recipe,
      title: entry.result.scene.title,
      narration: entry.result.scene.beats.map((b) => b.text).join("\n"),
    };
  }),
};
const literal = JSON.stringify(course)
  .replace(/</g, "\\u003c")
  .replace(/\u2028/g, "\\u2028")
  .replace(/\u2029/g, "\\u2029");

for (const { name, result } of planned)
  fs.writeFileSync(
    path.join(root, "examples", name + ".scene.json"),
    JSON.stringify(result.scene, null, 2) + "\n",
  );
const audit = planned.map(({ name, result }) => ({
  input: name + ".recipe.json",
  output: name + ".scene.json",
  ...result.trace,
}));
fs.writeFileSync(
  path.join(root, "evidence/e2/recipe-build.json"),
  JSON.stringify(audit, null, 2) + "\n",
);

fs.writeFileSync(
  path.join(root, "courses/token/course-data.js"),
  "// Generated from course manifest and recipe inputs. Do not edit.\nwindow.TokenCourse = " +
    literal +
    ";\n",
);

console.log("Compiled constrained recipe inputs and offline course data");
