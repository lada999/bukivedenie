# opencode

Write-capable agent for implementation and verification.

## Do
- Run the scoped test first.
- Implement the smallest change.
- Re-run tests.
- Run smoke and inspect artifacts.

## Allowed work shape
- Frontend code in `frontend/src/`
- Frontend tests in `frontend/tests/`
- Smoke runner in `scripts/ui_smoke.mjs`
- Artifacts in `artifacts/ui-smoke/`

## Required loop
1. `npm test`
2. Fix code
3. `npm test`
4. `npm run smoke`
5. Inspect logs, HTML, and screenshots

## Termux/container rule
- If a browser is unavailable, keep API and HTML snapshots working.
- If screenshots are available, save them; if not, do not block the whole loop.
