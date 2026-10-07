"use strict";
const fs = require("fs"),
  path = require("path");
const { compileRecipe } = require("../src/recipes.cjs");
const root = path.resolve(__dirname, "..");
// Validate every input before touching previous valid derived scenes.
const planned = ["course-water", "course-everyday", "e2-cloud"].map((name) => {
  const input = JSON.parse(
    fs.readFileSync(path.join(root, "recipes", name + ".recipe.json"), "utf8"),
  );
  return { name, result: compileRecipe(input) };
});
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
console.log("Compiled 3 constrained recipe inputs");
