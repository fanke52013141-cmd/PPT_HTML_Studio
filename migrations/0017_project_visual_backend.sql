-- Explicit visual backend selection for the HTML presentation route
-- (html-backend-development plan B01). Existing projects keep the image
-- pipeline; the HTML backend is opt-in per new project and cannot be
-- switched after creation in the initial release.
ALTER TABLE projects ADD COLUMN visual_backend VARCHAR(16) NOT NULL DEFAULT 'image';
