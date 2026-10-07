# Hanhan Model and Animation

## Structure
- `web/`: bilingual Three.js preview, controller and tests; `web/public/assets/` contains distributable GLB, state configurations and audio.
- `src/`: reproducible Blender Python sources and packaging utilities.
- `output/`: latest editable Blender model plus required base sources and standalone props. Older large work-in-progress files remain in the private local working directory.
- `reference/`: necessary character reference originals and third-party provenance; no credentials, payment records or unrelated project files.
- `qa/`: selected validation evidence; exclude caches, terminal dumps and machine-specific diagnostics.
- `docs/`: screenshots, credits and bilingual integration notes.
- `.github/workflows/pages.yml`: tests, build and GitHub Pages deployment.

## Conventions
- Preserve the accepted v4.7 round silhouette, hand/boot topology, 15 state animations and independent mouth/gaze controls.
- Keep Chinese and English UI strings and readme documents in sync. State IDs and APIs stay English.
- Animation tests inspect the actual GLB. Visual changes require browser inspection; browser QA does not validate Android behavior.
- Asset budget: 20k triangles including current props, 48 bones, 8 draw calls, 1024px textures and 5 MiB GLB.
- Build: `cd web && npm ci && npm test && npm run build`.
- GitHub Pages build: `cd web && VITE_BASE_PATH=/hanhan-model-and-animation/ npm run build`.
- Publication is authorized for this initial delivery. Future pushes and deployments follow the user's instructions.
- Never commit secrets, `.env`, `node_modules`, caches, `.blend1`, raw service downloads, or unrelated local files.
