**Frontend**

- Source of truth: `frontend/`
- Dev server: `npm run dev`
- Build: `npm run build`
- Deploy alias: `npm run deploy`
- Smoke: `npm run smoke`

The backend serves `frontend/index.html` and `frontend/dist/*`.

The smoke run follows the dashboard-first route and writes artifacts to `artifacts/ui-smoke/`.

If you need a manual check:

```bash
cd frontend
npm run dev
```
