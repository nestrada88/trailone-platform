# TrailOne production bundle

This bundle consolidates the uploaded FastAPI GPX service with a corrected production frontend and Docker deployment.

## What is fixed

- Same-origin frontend/API routing through NGINX inside the frontend container
- No external NGINX bind mounts
- No CORS dependency in browser requests
- Correct React + Vite + TypeScript configuration
- Working Docker compose layout
- Relative frontend API calls (`/v1/gpx/...`)

## URLs

- Frontend: `http://localhost:81`
- API docs: `http://localhost:8000/docs`
- API health through frontend proxy: `http://localhost:81/v1/gpx/health/ready`

## Start

```bash
docker compose up --build
```

## Stop

```bash
docker compose down
```

## Notes

- The frontend proxies `/v1/*` to the `api` service over the Docker network.
- The API is still published directly on port `8000` for Swagger and direct debugging.
