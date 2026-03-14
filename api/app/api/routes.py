
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
import gpxpy.gpx

from app.core.config import Settings, get_settings
from app.core.exceptions import GPXProcessingError
from app.models.schemas import AnalyzeResponse, DistanceRequest, DistanceResponse
from app.services.gpx_processing import (
    analyze_gpx,
    calculate_3d_distance,
    generate_waypoints,
    validate_request_inputs,
    build_enriched_gpx_bytes,
)

router = APIRouter(prefix='/v1/gpx', tags=['gpx'])


async def _read_upload(upload: UploadFile, settings: Settings) -> bytes:
    content = await upload.read()
    if not content:
        raise GPXProcessingError('Uploaded GPX file is empty.')
    if len(content) > settings.max_upload_size_bytes:
        raise GPXProcessingError(
            f'Uploaded GPX file exceeds the configured limit of {settings.max_upload_size_bytes} bytes.'
        )
    return content


@router.get('/health/live', tags=['health'])
async def live() -> dict:
    return {'status': 'ok'}


@router.get('/health/ready', tags=['health'])
async def ready(settings: Settings = Depends(get_settings)) -> dict:
    return {
        'status': 'ready',
        'app_name': settings.app_name,
        'version': settings.app_version,
        'max_points': settings.max_points,
    }


@router.post('/analyze', response_model=AnalyzeResponse)
async def analyze_endpoint(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> AnalyzeResponse:
    content = await _read_upload(file, settings)
    analysis = analyze_gpx(content, file.filename or 'upload.gpx', settings.max_points)
    parsed = analysis['parsed']
    return AnalyzeResponse(
        tracks=parsed['tracks'],
        segments=parsed['segments'],
        total_points=parsed['total_points'],
        elevation_statistics=analysis['elevation_statistics'],
    )


@router.post('/elevation', response_model=AnalyzeResponse)
async def elevation_endpoint(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> AnalyzeResponse:
    content = await _read_upload(file, settings)
    analysis = analyze_gpx(content, file.filename or 'upload.gpx', settings.max_points)
    parsed = analysis['parsed']
    return AnalyzeResponse(
        tracks=parsed['tracks'],
        segments=parsed['segments'],
        total_points=parsed['total_points'],
        elevation_statistics=analysis['elevation_statistics'],
    )


@router.post('/generate-waypoints')
async def generate_waypoints_endpoint(
    file: UploadFile = File(...),
    trail_prefix: str = Form(...),
    step_size: float = Form(...),
    distance_method: str = Form('auto'),
    settings: Settings = Depends(get_settings),
) -> Response:
    content = await _read_upload(file, settings)
    analysis = analyze_gpx(content, file.filename or 'upload.gpx', settings.max_points)
    gpx = analysis['gpx']
    parsed = analysis['parsed']

    validate_request_inputs(gpx, file.filename or 'upload.gpx', trail_prefix, step_size)
    waypoints = generate_waypoints(
        parsed['points'],
        trail_prefix,
        step_size,
        distance_method=distance_method,
    )
    gpx_bytes = build_enriched_gpx_bytes(gpx, waypoints)
    stem = (file.filename or 'trail').rsplit('.', 1)[0]
    output_filename = f'{stem}_{step_size}_wpt.gpx'
    headers = {
        'Content-Disposition': f'attachment; filename="{output_filename}"',
        'X-Waypoints-Generated': str(len(waypoints)),
    }
    return Response(content=gpx_bytes, media_type='application/gpx+xml', headers=headers)


@router.post('/distance', response_model=DistanceResponse)
async def distance_endpoint(payload: DistanceRequest) -> DistanceResponse:
    point1 = gpxpy.gpx.GPXTrackPoint(
        latitude=payload.point1.latitude,
        longitude=payload.point1.longitude,
        elevation=payload.point1.elevation,
    )
    point2 = gpxpy.gpx.GPXTrackPoint(
        latitude=payload.point2.latitude,
        longitude=payload.point2.longitude,
        elevation=payload.point2.elevation,
    )
    distance_m, method = calculate_3d_distance(
        point1,
        point2,
        distance_method=payload.distance_method,
        dataset_size=payload.dataset_size,
    )
    return DistanceResponse(
        distance_m=round(distance_m, 3),
        distance_km=round(distance_m / 1000, 6),
        distance_method_used=method,
    )
