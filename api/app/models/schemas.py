
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


DistanceMethod = Literal['auto', 'geodesic', 'haversine']


class WaypointParams(BaseModel):
    trail_prefix: str = Field(..., description='3-6 uppercase letters, e.g. LCST')
    step_size: float = Field(..., gt=0, le=100, description='Kilometer interval for generated markers')
    distance_method: DistanceMethod = Field(default='auto')

    @field_validator('trail_prefix')
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        if not value.isalpha() or not value.isupper() or not (3 <= len(value) <= 6):
            raise ValueError('trail_prefix must contain 3-6 uppercase letters.')
        return value


class PointPayload(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    elevation: Optional[float] = None


class DistanceRequest(BaseModel):
    point1: PointPayload
    point2: PointPayload
    distance_method: DistanceMethod = Field(default='auto')
    dataset_size: Optional[int] = Field(default=None, ge=2)


class ParseSummary(BaseModel):
    tracks: int
    segments: int
    total_points: int


class ElevationStatistics(BaseModel):
    total_ascent: float
    total_descent: float
    max_elevation: float
    min_elevation: float
    elevation_range: float


class AnalyzeResponse(BaseModel):
    tracks: int
    segments: int
    total_points: int
    waypoints_generated: Optional[int] = None
    elevation_statistics: ElevationStatistics


class DistanceResponse(BaseModel):
    distance_m: float
    distance_km: float
    distance_method_used: DistanceMethod | Literal['geodesic', 'haversine']
