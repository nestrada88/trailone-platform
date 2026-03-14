export type DistanceMethod = "auto" | "geodesic" | "haversine";

export interface PointPayload {
  latitude: number;
  longitude: number;
  elevation?: number | null;
}

export interface DistanceRequest {
  point1: PointPayload;
  point2: PointPayload;
  distance_method: DistanceMethod;
  dataset_size?: number;
}

export interface DistanceResponse {
  distance_m: number;
  distance_km: number;
  distance_method_used: DistanceMethod | "geodesic" | "haversine";
}

export interface AnalyzeResponse {
  tracks: number;
  segments: number;
  total_points: number;
  waypoints_generated?: number | null;
  elevation_statistics: {
    total_ascent: number;
    total_descent: number;
    max_elevation: number;
    min_elevation: number;
    elevation_range: number;
  };
}

const API_BASE = "/v1/gpx";

async function ensureOk(response: Response) {
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      message = payload?.detail || payload?.message || message;
    } catch {
      // Keep default fallback
    }
    throw new Error(message);
  }
  return response;
}

export async function getReadyHealth(): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE}/health/ready`);
  await ensureOk(response);
  return response.json();
}

export async function analyzeGpx(file: File): Promise<AnalyzeResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    body: formData
  });

  await ensureOk(response);
  return response.json();
}

export async function generateWaypoints(
  file: File,
  trailPrefix: string,
  stepSize: number,
  distanceMethod: DistanceMethod = "auto"
): Promise<{ blob: Blob; filename: string | null; generatedCount: string | null }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("trail_prefix", trailPrefix);
  formData.append("step_size", String(stepSize));
  formData.append("distance_method", distanceMethod);

  const response = await fetch(`${API_BASE}/generate-waypoints`, {
    method: "POST",
    body: formData
  });

  await ensureOk(response);
  const disposition = response.headers.get("Content-Disposition");
  const filenameMatch = disposition?.match(/filename="([^"]+)"/);
  return {
    blob: await response.blob(),
    filename: filenameMatch?.[1] ?? null,
    generatedCount: response.headers.get("X-Waypoints-Generated")
  };
}

export async function calculateDistance(payload: DistanceRequest): Promise<DistanceResponse> {
  const response = await fetch(`${API_BASE}/distance`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  await ensureOk(response);
  return response.json();
}
