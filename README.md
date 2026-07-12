# TrailOne GPX Toolkit

TrailOne is a full-stack web application for working with GPX hiking and trail data. It lets you upload a GPX file, validate and analyze the route, and generate a new GPX file enriched with distance-based waypoints and key trail markers.

## What this solution does

The application has two main parts:

- A FastAPI backend that parses GPX files, validates them, computes elevation and distance metrics, and generates enriched GPX output.
- A React + Vite frontend that provides a simple browser-based workflow for uploading a file and downloading the result.

This makes the workflow suitable for trail planning, route review, and creating navigational marker files for hiking routes.

## Main features

- Upload and validate GPX files
- Analyze route structure and track statistics
- Calculate cumulative 3D distance along the route
- Generate waypoints at fixed kilometer intervals
- Add special markers for:
  - trail head
  - trail end
  - highest point
  - lowest point
  - halfway point
- Download the enriched GPX file directly from the browser
- Expose the same functionality through a REST API for scripting or integration

## Project structure

- [api/app/main.py](api/app/main.py) — FastAPI application entry point
- [api/app/api/routes.py](api/app/api/routes.py) — API endpoints for health, analysis, waypoint generation, and distance calculation
- [api/app/services/gpx_processing.py](api/app/services/gpx_processing.py) — GPX parsing, validation, statistics, and waypoint generation logic
- [frontend/src/components/WaypointGenerator.tsx](frontend/src/components/WaypointGenerator.tsx) — browser UI for generating waypoint-enriched GPX files
- [frontend/src/api/client.ts](frontend/src/api/client.ts) — frontend client for calling the API
- [docker-compose.yml](docker-compose.yml) — container orchestration for API and frontend

## Prerequisites

To run the application locally, you need:

- Docker Desktop or Docker Engine with Docker Compose
- Optional for local Python development:
  - Python 3.11+
  - Node.js 18+

## Running with Docker Compose

The simplest way to run the full solution is with Docker.

### Start the application

```bash
docker compose up --build
```

### Access the application

- Frontend: http://localhost:81
- API documentation: http://localhost:8000/docs
- API health endpoint: http://localhost:81/v1/gpx/health/ready

### Stop the application

```bash
docker compose down
```

## Running locally without Docker

### Backend

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:5173.

## Using the web interface

1. Open the frontend in your browser.
2. Select a GPX file from your computer.
3. Enter a trail prefix (for example, `LCST`).
4. Set a step size in kilometers (for example, `1` for 1 km markers).
5. Choose a distance method:
   - `auto` — recommended default
   - `geodesic` — more accurate geodesic approximation
   - `haversine` — faster approximate spherical calculation
6. Click “Generate and download”.

The application will download a new GPX file with additional waypoints based on the selected interval.

## Using the REST API

The backend exposes the following endpoints:

- `GET /v1/gpx/health/live`
- `GET /v1/gpx/health/ready`
- `POST /v1/gpx/analyze`
- `POST /v1/gpx/elevation`
- `POST /v1/gpx/generate-waypoints`
- `POST /v1/gpx/distance`

### Health check

```bash
curl http://localhost:8000/v1/gpx/health/ready
```

### Analyze a GPX file

```bash
curl -X POST \
  -F "file=@trail.gpx" \
  http://localhost:8000/v1/gpx/analyze
```

### Generate waypoint-enriched GPX

```bash
curl -X POST \
  -F "file=@trail.gpx" \
  -F "trail_prefix=LCST" \
  -F "step_size=1" \
  -F "distance_method=auto" \
  http://localhost:8000/v1/gpx/generate-waypoints \
  --output lcst_waypoints.gpx
```

### Calculate distance between two points

```bash
curl -X POST http://localhost:8000/v1/gpx/distance \
  -H "Content-Type: application/json" \
  -d '{
    "point1": {"latitude": 40.0, "longitude": -3.0, "elevation": 100.0},
    "point2": {"latitude": 40.01, "longitude": -3.01, "elevation": 120.0},
    "distance_method": "auto"
  }'
```

## Input requirements

The GPX uploader expects:

- a valid GPX file with `.gpx` extension
- at least one track and one track segment
- at least two track points
- valid latitude and longitude values

The backend also enforces sensible limits for uploaded file size and number of points.

## Configuration

The backend uses environment variables with the `TRAILONE_` prefix. The defaults are defined in [api/app/core/config.py](api/app/core/config.py).

Useful settings include:

- `TRAILONE_APP_NAME`
- `TRAILONE_APP_VERSION`
- `TRAILONE_DEBUG`
- `TRAILONE_LOG_LEVEL`
- `TRAILONE_MAX_UPLOAD_SIZE_BYTES`
- `TRAILONE_MAX_POINTS`

Example:

```bash
export TRAILONE_MAX_UPLOAD_SIZE_BYTES=52428800
export TRAILONE_LOG_LEVEL=DEBUG
```

## Expected output

When waypoint generation succeeds, the downloaded GPX file contains:

- the original route geometry preserved from the uploaded GPX
- new waypoint entries inserted at the requested interval distance
- markers for the trail head, trail end, highest point, lowest point, and halfway point

## Troubleshooting

- If the frontend cannot reach the API, confirm that both Docker services are running and that the frontend is using the same-origin proxy path.
- If uploads fail, verify that the file is a valid GPX file and that it is not too large.
- If the API returns validation errors, check that the GPX file contains track points and that the coordinates are valid.
- If you want to inspect the API behavior interactively, open the Swagger UI at http://localhost:8000/docs.

## Notes

- The frontend proxies `/v1/*` requests to the API over the Docker network, so browser requests do not need manual CORS configuration.
- The API remains directly accessible on port `8000` for debugging and direct integration use.
