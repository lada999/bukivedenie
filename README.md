**Start Here**

1. Enter the Nix dev shell: `nix develop`
2. Install frontend deps: `make frontend-install`
3. Start development: `make dev`
4. Open the app at `http://127.0.0.1:5173`
5. Build for checks or release: `make frontend-build`

**Nix shell**

- Uses the system `nixpkgs` input via `<nixpkgs>`.
- Targeted baseline: `25.11`.
- Available tools: `python3`, `pytest`, `nodejs`, `chromium`, `git`, `curl`, `make`.
- `nix develop` is the fastest way to get the full build/test environment.
- If `direnv` is installed, run `direnv allow` once in the repo and the shell will load automatically.
- `CHROME_PATH` is set inside the shell for smoke runs.

**Where to edit**

- UI code: `frontend/src/`
- Entry and routing: `frontend/src/main.js`, `frontend/src/router.js`
- API layer: `frontend/src/api.js`
- Backend API: `src/webapp.py`

**Helpful commands**

- `nix develop` - enter the dev shell
- `pytest` - run backend tests inside the shell
- `node --version` - verify Node availability
- `make ui-smoke` - run the browser smoke check and write artifacts to `artifacts/ui-smoke/`
- `python -m src.webapp --host 127.0.0.1 --port 8000` - start only the backend

The canonical UI lives in `frontend/`.
The backend serves `frontend/index.html` and `frontend/dist/*`.
