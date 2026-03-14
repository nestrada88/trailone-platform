# TrailOne GPX FastAPI Bundle

This bundle refactors the original CLI GPX waypoint generator into a production-oriented FastAPI service.

## Scope

The API exposes:

- GPX health endpoints
- GPX analysis
- elevation statistics
- waypoint generation and enriched GPX download
- point-to-point 3D distance calculation

## Project Layout

```text
trailone_fastapi_bundle/
├── app/
│   ├── api/routes.py
│   ├── core/
│   ├── models/
│   ├── services/
│   └── main.py
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

## Endpoints

- `GET /v1/gpx/health/live`
- `GET /v1/gpx/health/ready`
- `POST /v1/gpx/analyze`
- `POST /v1/gpx/elevation`
- `POST /v1/gpx/generate-waypoints`
- `POST /v1/gpx/distance`

## Example: Analyze

```bash
curl -X POST       -F "file=@trail.gpx"       http://localhost:8000/v1/gpx/analyze
```

## Example: Generate waypoint-enriched GPX

```bash
curl -X POST       -F "file=@trail.gpx"       -F "trail_prefix=LCST"       -F "step_size=1"       -F "distance_method=auto"       http://localhost:8000/v1/gpx/generate-waypoints       --output lcst_waypoints.gpx
```

## Production Notes

This bundle includes the following production-oriented changes relative to the CLI:

- separation of transport, schema, and service layers
- centralized exception handling
- environment-backed settings
- request-size and point-count limits
- byte-oriented GPX parsing for uploaded files
- in-memory GPX response generation instead of persistent artifact sprawl
- Docker packaging

## Direct Relationship to the Original Script

The computational core remains based on the uploaded CLI implementation in `gpx_trail_wpt.py`, with CLI-specific concerns removed and REST transport added.
