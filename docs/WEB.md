# Web Application

Step 41/42 adds a browser version beside the existing desktop simulator.

## Architecture

- `web/`: Next.js + React + TypeScript frontend
- `api/index.py`: stateless FastAPI endpoints
- Existing Python folders remain the shared robotics engine

The web deployment uses same-origin relative API routes such as `/api/scenarios`; no hardcoded localhost or production domain is required.

## Local web development

Install frontend dependencies:

```powershell
cd web
npm install
npm run dev
```

For the full local web app, use the default dev command inside `web/`:

```powershell
cd web
npm run dev
``` 

This starts the Python FastAPI server on port 8787 using the project `.venv`, and Next.js on port 3000. Use `npm run dev:web` only when you intentionally want frontend-only mode. The Next.js dev server rewrites `/api/...` to the local Python server only in development. Production still uses same-origin Vercel routing.

## Python dependencies

- `requirements.txt` is the minimal web/API deployment set.
- `requirements-desktop.txt` includes the desktop and test dependencies such as Pygame and pytest.

## API endpoints

- `GET /api/health`
- `GET /api/scenarios`
- `POST /api/simulation/reset`
- `POST /api/simulation/step`
- `POST /api/simulation/goal`
- `POST /api/planner/plan`
- `POST /api/mission/parse`

The API is designed for stateless serverless execution: requests send the current robot/scenario data and receive the next state or computed result.

## Desktop preserved

The original `python main.py` Pygame simulator remains available and still owns the full desktop logging, replay, custom map, and experiment workflows.