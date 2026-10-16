# Design System: PPT HTML Studio — Course Production Workspace

## 1. Visual Theme & Atmosphere
Retain the existing PPT Studio identity. The user authorized the new private Stitch project 16819466348601712538 for the six-step redesign; selected screens are recorded in six-step-workspace-20261015.json. Project 8494304199748819775 remains historical reference. A focused Chinese-language creation studio, balanced density 5, structured variance 4, restrained motion 2. The actual course/page preview is the focal point. Business facts, pending decisions and the next meaningful action outrank decoration. Application UI dimensions in docs/ui-spec.md override generated screen suggestions.

## 2. Color Palette & Roles
- Canvas Slate (#F7F8FA): application canvas.
- Pure Surface (#FFFFFF): working surface and preview panels.
- Charcoal Ink (#20252D): headings and primary content; never pure black.
- Slate Text (#687180): supporting text and metadata.
- Quiet Border (#E4E7EB): separators and structural boundaries.
- Studio Orange (#EE5D36): single restrained accent for the primary action, current step and focus.
- Accent Wash (#FFF5F0): active navigation surface. No competing saturated accent, gradient button or glow.
State labels use explicit words/icons as well as neutral contrast; color alone must never communicate approval or failure.

## 3. Typography Rules
Use the application's available Noto Sans SC/Microsoft YaHei stack. Sans-serif throughout. Workspace title 18px; section title 16px/1.5 at 600; body 14–16px/1.65; labels 13–14px/1.5. Counters and timestamps use tabular numerals. No display-serif, giant marketing headline, or decorative headline collage in this software workspace. Limit explanation lines to roughly 65 characters.

## 4. Component Stylings
One primary action in each decision area. Secondary actions use quiet outlines or text treatment; technical settings are disclosed progressively. Titlebar tools use the existing compact 30px contract; content buttons keep 44px targets, 8px corners and clear keyboard focus/disabled/busy states. Dividers and aligned spacing replace stacks of nested cards. Main preview surface uses 12px corners and a restrained shadow only to separate it from the canvas. Inputs have labels above, helper/error text below, and no floating labels. Empty states say which predecessor is missing and provide a navigation action. Real status distinguishes generated, awaiting confirmation, stale, blocked, running and complete. Waiting operations use subtle opacity motion and a real progress label; respect reduced motion.

## 5. Layout Principles
Desktop: a compact top bar for project identity, a 210–224px step rail, and one main working surface. At >=1100px use a dominant preview with a narrower decision/inspector column. At 768–1099px stack inspector below preview; below 768px collapse all content grids to one column and use a compact navigation treatment. No horizontal overflow at 420/768/1280px. Containers have min-width:0; grid columns use minmax(0,1fr). Use 8/12/16/24/32px spacing, 24–32px panel padding and a consistent maximum content width of 1440px.
The step rail is the only full-process navigator; do not repeat it as four giant equal cards. A compact breadcrumb or status strip can explain the current substage. Page selector and current stage title sit together, settings stay secondary, and a fixed header must not consume a third of a narrow window. Preview images fit their container without cropping. A project/page name is navigation metadata, not a requirement to render a title on every course frame.

## 6. Motion & Interaction
Tactile button press via transform, subtle opacity transitions and a restrained progress pulse only while actual work is running. No constant motion on idle content. Transitions 140–220ms with non-linear easing, reduced-motion disables movement. Shared playback uses the actual audio time as the single clock; timeline seeking, pause and sentence selection must update the same rendered frame. Never decorate a test fixture as a real successful course.

## 7. Anti-Patterns
No emoji labels, neon gradients, pure-black fills, generic three-equal-card rows, huge ornamental whitespace, repeated process navigation, fake progress, placeholder success metrics, hidden prerequisites, automatic approvals or a prominent batch-image action that bypasses design confirmation. Do not expose raw hashes/JSON in the main decision area. No obsolete Mask/handwriting controls on the HTML route. Every visible action maps to a real existing operation, or clearly explains the registered capability boundary.

## 8. Business Screen Contract
Article → storyboard → full-page design image and human confirmation → independent assets plus controlled HTML reconstruction/animation → narration/audio and synchronized sentence review → optional digital human → formal output. Keep confirmed reference viewable beside the actual page. Review/accept controls depend on current inputs and evidence. Multi-asset boards are a manual auxiliary with the current automatic one-subject budget explicitly stated. Independent page, design, audio and semantic facts determine progress; legacy image step numbers do not prove completion.
