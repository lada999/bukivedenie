# AGENTS

Minimal rules for agent work in this repo.

## Roles
- `pi`: read-first, plan-first, TDD-first. Produces tests, smoke plans, and patch outlines.
- `opencode`: write-capable implementer. Runs tests, builds, smoke checks, and collects artifacts.

## Shared rules
- Keep changes small and local.
- Prefer the simplest working path.
- Use TDD: failing test first, then minimal fix, then verify.
- For frontend visualizations, always collect artifacts: logs, HTML snapshot, and screenshot when possible.
- Keep browserless smoke available so work can proceed in container and Termux-style environments.
- Use the Nix shell for all build, test, and smoke work when available.
- Preferred entry: `direnv allow` once, then `nix develop` or just enter the repo shell.
- The shell should provide `python3`, `pytest`, `node`, `chromium`, `git`, `curl`, and `make`.
- Prefer Nix-provided tools over host binaries for reproducibility.

## Canonical workflow
1. Read the relevant surface files.
2. Add or update a failing test.
3. Implement the smallest fix.
4. Enter the Nix shell with `nix develop` if not already active.
5. Run `pytest`, `npm test`, or the smallest scoped test target from inside the shell.
6. Run `npm run smoke` or `make ui-smoke` from inside the shell.
7. Inspect `artifacts/ui-smoke/`.

## Artifact conventions
- Use `artifacts/ui-smoke/` for smoke output.
- Save `report.json`, `api.json`, `console.log`, `html/*.html`, and `screens/*.png` when a browser is available.
- Route names should be slugged, not raw hash fragments.

## File map
- `agents/pi.md`: pi-specific contract and TDD checklist.
- `agents/opencode.md`: opencode-specific execution contract.
- `frontend/tests/`: frontend unit and smoke helper tests.
- `scripts/ui_smoke.mjs`: canonical browserless/browser smoke runner.

## HDS note
- If a change affects a public contract, document it before or with the code change.
