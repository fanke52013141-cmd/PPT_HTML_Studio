# Design System: PPT Studio 标注视频校准

## 1. Visual Theme & Atmosphere
Stitch-oriented design specification for an existing production editing tool. Density 5, variance 4, motion 2. The video is the primary work surface; a narrow right inspector keeps the editing sequence readable. Preserve the workspace shell governed by docs/ui-spec.md. No marketing hero, decorative image or unrelated dashboard metric.

## 2. Color Palette & Roles
- Surface White #FFFFFF: modal, controls and inspector.
- Workspace Slate #F8FAFC: video stage and subdued sections.
- Text Ink #0F172A: titles and primary button.
- Secondary Slate #475569: instructions and numeric clock.
- Border Slate #E2E8F0: dividers and secondary buttons.
- Brand Orange #F46A38: existing project accent and focus indication. Soft tint #FFF0EA. Preserve this mandated brand color instead of introducing a plugin-default accent; project instructions take priority over the skill's saturation preference.

## 3. Typography Rules
Reuse Microsoft YaHei / PingFang SC / existing sans-serif stack. Header 20px, section title 14px, body 14px with 1.6 line-height. Clock uses a monospace stack and tabular figures. Do not load remote fonts or change shared workspace typography. No serif or oversized display headline.

## 4. Component Stylings
One primary action: dark filled “保存并更新预览”. Secondary actions are white, 1px outlined, 8px radius. Modal radius 16px; 24px content padding on desktop. Labels sit above controls. Focus is visible. Player controls are scoped separately to protect their native SVG icons from global button styling. The player's actual video and audio remain unchanged.

## 5. Layout Principles
Max width 1360px. CSS Grid with flexible video column and 288px inspector. Video has a distinct, uncluttered surface; frame navigation and clock sit below it. Inspector contains three ordered sections: selection, timing, geometry. Footer separates feedback and save action. Below 900px collapse to one column; below 768px use 16px padding and 44px touch targets. No horizontal overflow, equal three-card row or overlaid editorial content.

## 6. Motion & Interaction
Restrained opacity/transform transitions for controls. No perpetual animation during precise audio or frame calibration; this is a deliberate project-specific adaptation of the skill's motion defaults. Respect prefers-reduced-motion. Do not animate dimensions or move the video under the cursor.

## 7. Anti-Patterns (Banned)
No neon, gradient headings, new accent colors, emoji decoration, marketing filler, invented accuracy figures, giant pill buttons or scattered action rows. No absolute-positioned instructional text over the video. Never make an old preview look refreshed after an edit.
