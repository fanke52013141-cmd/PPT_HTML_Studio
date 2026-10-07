# Design System: PPT Studio task feedback

## 1. Visual Theme & Atmosphere
A compact production workspace, density 8, variance 2, motion 3. Preserve the shell in docs/ui-spec.md and approved Stitch references. One status belongs to one actual operation or page. Existing content stays readable during regeneration.

## 2. Color Palette & Roles
White #FFFFFF surfaces; slate #f7f8fc canvas; charcoal #17191d text and advance actions; #64748b secondary text; #e2e8f0 dividers. Existing brand #ee5d36 is the only action accent. Neutral pending states, orange active work, semantic green completion and red errors reuse existing tokens.

## 3. Typography Rules
Keep installed Chinese sans-serif fonts and existing app font stack. Labels 12px, inputs 14px/1.5, headings 14px/600. Tabular numerals for real elapsed time and server progress. No new web fonts.

## 4. Component Stylings
Use underline inputs with 6px vertical padding. Stage content padding 12–16px, 8px field gaps. First-load skeletons match content dimensions. Running tasks use a horizontal moving segment, never an isolated circular spinner. Waiting, queued, running, generated, confirmed, failed, paused and network reconnecting have distinct text. Image and audio generation status is per page. Storyboard has separate script and visualization status. Errors stay inline; existing copy/error recovery actions remain available.

## 5. Layout Principles
Reuse eight stable visible steps. Status sits beside its heading or in the affected card. Never replace an existing image with a fabricated preview. Content can grow when narration wraps. Collapse content columns at narrow viewports; preserve existing toolbar navigation geometry.

## 6. Motion & Interaction
Animate transform and opacity only. Skeletons and running indicators animate only while a real load/job is active. Respect prefers-reduced-motion. aria-busy marks active work, role=status announces changes politely. Real percentages only when supplied by the server; indefinite jobs display current stage, never invented time or progress.

## 7. Anti-Patterns
No neon palettes, gratuitous cards, fake completion, arbitrary progress, invented ETA, or duplicate status explanations. Do not trigger paid model requests to demonstrate a loader. Reference demos are explicitly labeled and do not write project state.

## Content-level generation states
Preserve the existing orange #ee5d36 workspace, sans-serif typography, compact horizontal dividers and 8-step navigation. Article generation uses a four-line text skeleton in its output area. Storyboard script generation uses narration skeletons; visualization uses two columns for visual text and speech. Image generation preserves the project aspect ratio with pending, queued, running, generated states. Audio shows each page's audio-sized placeholder and pending/running/completed label. Mask and digital-human tasks occupy their content area and retain a visible completion message. Output uses a full-width rendering surface and actual job progress; never fabricate percentages. Motion is restrained opacity pulsing, disabled by reduced-motion preference. Keep existing results and editable content intact during regeneration. Word count belongs immediately after the script phase status. Narration dividers are always orange. Do not rely on spinner icons or sidebar state alone.

Generation replaces the output region in place rather than appending a status card. Preserve original content DOM and hidden state, restoring it on completion or failure. The preview uses an entire workspace with stage navigation, not a gallery of badges. Visualization retains the completed script above the mapping skeleton.

## Review candidate: restrained single-motion loading
User override: use a small rotating ring, not skeleton shimmer or marquee progress. During initial script/visual generation, show one uncluttered content viewport with a centered 26px spinner and one 14px neutral sentence. Remove the empty-storyboard card, bottom switching/help paragraph and stop button from this candidate. Retain the actual workspace header. Image cards keep static 12px status labels with no pulse, no moving indicator, no marquee border. Only the image preview contains a 24px spinner. Queued and pending cards remain static; generated cards display their image. Preview only until the user approves; production code is unchanged this iteration. Palette #ee5d36 accent, #ffffff surface, #f7f9fb canvas, #64748b text, #e2e8f0 border; existing sans-serif typography. Motion exclusively rotates the ring; honor reduced motion. Do not invent progress or initiate generation.

## Page-specific review refinement
Storyboard shows slide tabs and two phase sections; script generation reserves title/narration space with static neutral placeholders and one spinner. Visualization preserves the saved script and loads only the mapping region. Audio retains each page narration and loads inside its player slot. Images keep independent card states and offer preview controls for one automatic retry versus final two-attempt failure. Mask, digital-human and output reserve the result frame with static metadata. Exactly one motion per active output region; labels remain static. Production UI awaits approval.

## Approved production application
The refined preview is approved. Use a 28–30px two-tone orange ring with a static neutral track, one rotation only. Content enters with a 240ms opacity and 4px translation transition. Retain page structure and phase-specific output regions; remove legacy marquee, pulse indicators and morphing placeholders. Status labels stay static. Honor reduced motion.
