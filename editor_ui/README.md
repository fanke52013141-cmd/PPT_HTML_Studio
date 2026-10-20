# HTML editor UI adapters

Local build package; no server or replacement player. The production editor uses
the canvas-only bundle inside its iframe and a separate timeline bundle in the
editor panel. The combined editor.js remains an isolated P0 prototype.

From the repository root:

```powershell
npm.cmd ci --prefix editor_ui --ignore-scripts --registry=https://registry.npmjs.org
npm.cmd run build --prefix editor_ui
npm.cmd test --prefix editor_ui
```

Editor source and consumer files use the LF rules in `.gitattributes` because
the manifests hash exact bytes. Archived license files and generated outputs
retain their original bytes; some upstream licenses contain CRLF. Rebuild with
`build.mjs` after changing a consumer, and commit the regenerated manifests with
the source. Do not rewrite hashes by hand or normalize archived licenses.
The build tests exercise Git checkout with `core.autocrlf` both enabled and disabled.

Run `checks/test_html_scene_editor_fixture.py <temporary-directory>` with the
repository Python environment. Open the printed localhost root for the production
editor fixture; `/adapter-test` is P0. Add `--semantic` for synthetic 0.6 beats,
or `--presentation` for 0.7 with real header/text presentation variants.
Fixtures use temporary data, never application data, models or TTS. Ctrl+C stops
it. Browser regression exports in `checks/test_html_editor_layout.browser.mjs`
accept a cua Tab: on a fresh fixture execute `verifyMarqueeAndSnapSteps(tab)`
to check exact marquee membership, one-undo group movement, enabled/disabled slot
snapping and snapping to a displaced object. In a separate fresh tab execute
`verifyEditorLayoutSteps(tab)` in stages, then
`verifyLateLayoutPreview(tab)` for close/reopen during delayed preview.
These browser exports are test definitions, not evidence until executed. The
0.7 HTTP service regression is `checks/test_html_editor_layout_acceptance.py`;
it validates preview/save/reopen/no-op/conflict and semantic/style preservation,
but cannot certify pointer gestures or rendered capacity.
The 2026-10-17 real-browser run passed the four marquee/snap checks, all thirteen
0.7 workflow checks, and delayed-preview lifecycle checks. Evidence and remaining
coverage are recorded in the linked handoff. Edge guides exclude implicit gap
snapping; test approaches avoid competing valid guide lines.

- `src/canvas.js`: iframe Moveable/Selecto proxies; drag/resize, image ratio,
  group drag, optional guides and explicit destruction.
- `src/commands.mjs`: pure coordinates/binding conversions and atomic presentation
  operations. Caller owns validation and history.
- `static/html_editor_canvas.js`: production lifecycle bridge. Main editor owns
  drafts and commits after the existing preview service validates candidates.
- `src/timeline.jsx`: local React editing root with external seek/cursor and
  empty effects; no independent playback clock. `static/html_editor_timeline_bridge.js`
  owns production audio currentTime, lifecycle and calls into author transactions.
- `build.mjs`: generates separate canvas and P0 bundles under `static/editor_ui`,
  source/output manifests and notices. Rebuild generated assets. Canvas excludes
  React/timeline in the canvas bundle. Build snapshots pin production sources, consumers, lockfile,
  license evidence and output under tooling.

`licenses/records.json` records archived evidence and pinned sources. Missing npm
license files were supplemented with distinct provenance: cfcs uses a fixed
upstream commit because its published gitHead was unavailable; croact has a
reconstructed MIT notice from its published license/copyright declaration.
timeline-engine ISC metadata versus upstream MIT remains explicit and does not
enter production canvas. Build executable notices are distinct from browser
notices. These records are not legal certification; review actual distribution
scope before release. `archive_licenses.py` is a manual refresh tool, not a
network step during normal builds.

See [P1 evidence and remaining acceptance](../docs/plans/html-backend-development/handoff-editor-layout-p1-2026-10-17.md).

Latest [P2 implementation and evidence](../docs/plans/html-backend-development/handoff-editor-timeline-p2-2026-10-17.md).
Audio artifact guards, explicit draft-preserving refresh and existing narration
copy acceptance are in the [audio freshness handoff](../docs/plans/html-backend-development/handoff-editor-audio-freshness-2026-10-17.md).
`checks/test_html_editor_timeline.browser.mjs` verifies real UI gestures with
synthetic silent audio, plus timeline cursor and no-audio read-only modes. Actual
narration, re-TTS and video output still require separate acceptance. Source and
license closures include declared runtime dependencies already inlined by
upstream distribution bundles, not only esbuild's visible module inputs.
