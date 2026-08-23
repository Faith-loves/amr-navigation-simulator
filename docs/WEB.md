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

For Vercel-style local API routing, use Vercel dev from the repository root after installing the Vercel CLI.

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