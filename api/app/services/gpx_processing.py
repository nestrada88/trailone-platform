
from __future__ import annotations

import copy
import io
import math
import re
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional, Sequence

import gpxpy
import gpxpy.gpx
from geopy.distance import geodesic

from app.core.exceptions import GPXProcessingError

EARTH_RADIUS_M = 6_371_000
AUTO_METHOD_THRESHOLD = 50_000


def validate_request_inputs(gpx, filename: str, trail_prefix: str, step_size: float) -> None:
    if not isinstance(trail_prefix, str) or not re.fullmatch(r'[A-Z]{3,6}', trail_prefix):
        raise GPXProcessingError(
            'Trail prefix must contain 3-6 uppercase letters (example: HIK, LCST).'
        )

    if not isinstance(step_size, (int, float)):
        raise GPXProcessingError('Step size must be numeric.')
    if step_size <= 0:
        raise GPXProcessingError('Step size must be greater than zero.')
    if step_size > 100:
        raise GPXProcessingError('Step size is unrealistically large (>100 km).')

    if filename and not filename.lower().endswith('.gpx'):
        raise GPXProcessingError("Uploaded file must use the '.gpx' extension.")

    if not gpx.tracks:
        raise GPXProcessingError('GPX file contains no <trk> elements.')

    track = gpx.tracks[0]
    if not track.segments:
        raise GPXProcessingError('GPX track contains no <trkseg> elements.')

    segment = track.segments[0]
    if not segment.points:
        raise GPXProcessingError('GPX segment contains no <trkpt> elements.')
    if len(segment.points) < 2:
        raise GPXProcessingError('GPX track must contain at least two points.')

    for idx, point in enumerate(segment.points):
        if point.latitude is None or point.longitude is None:
            raise GPXProcessingError(f'Track point {idx} has missing coordinates.')
        if not (-90 <= point.latitude <= 90):
            raise GPXProcessingError(f'Invalid latitude at point {idx}: {point.latitude}')
        if not (-180 <= point.longitude <= 180):
            raise GPXProcessingError(f'Invalid longitude at point {idx}: {point.longitude}')
        if point.elevation is not None and not (-1000 <= point.elevation <= 9000):
            raise GPXProcessingError(
                f'Unrealistic elevation at point {idx}: {point.elevation}'
            )


def parse_gpx_bytes(content: bytes):
    try:
        return gpxpy.parse(content.decode('utf-8'))
    except UnicodeDecodeError as exc:
        raise GPXProcessingError('GPX payload must be valid UTF-8 text.') from exc
    except Exception as exc:
        raise GPXProcessingError(f'Unable to parse GPX payload: {exc}') from exc


def parse_gpx_file(gpx, strict: bool = True, max_points: int = 200_000) -> dict:
    if not gpx.tracks:
        raise GPXProcessingError('GPX file contains no <trk> elements.')

    all_points = []
    track_count = len(gpx.tracks)
    segment_count = 0

    for track in gpx.tracks:
        if not track.segments:
            if strict:
                raise GPXProcessingError('Track contains no <trkseg> elements.')
            continue

        for segment in track.segments:
            segment_count += 1
            if not segment.points:
                if strict:
                    raise GPXProcessingError('Track segment contains no <trkpt> elements.')
                continue
            all_points.extend(segment.points)

    if not all_points:
        raise GPXProcessingError('No valid track points found in GPX file.')
    if len(all_points) < 2:
        raise GPXProcessingError('GPX track must contain at least two points.')
    if len(all_points) > max_points:
        raise GPXProcessingError(
            f'GPX file contains too many points ({len(all_points)}). Maximum allowed is {max_points}.'
        )

    if strict:
        for index, point in enumerate(all_points):
            if point.latitude is None or point.longitude is None:
                raise GPXProcessingError(f'Missing coordinates at point {index}')
            if not (-90 <= point.latitude <= 90):
                raise GPXProcessingError(f'Invalid latitude at point {index}: {point.latitude}')
            if not (-180 <= point.longitude <= 180):
                raise GPXProcessingError(f'Invalid longitude at point {index}: {point.longitude}')

    return {
        'points': all_points,
        'tracks': track_count,
        'segments': segment_count,
        'total_points': len(all_points),
    }


def compute_elevation_statistics(trackpoints) -> dict:
    total_ascent = 0.0
    total_descent = 0.0
    max_elevation = None
    min_elevation = None
    prev_elevation = None

    for point in trackpoints:
        elevation = getattr(point, 'elevation', None)
        if elevation is None:
            continue

        if max_elevation is None or elevation > max_elevation:
            max_elevation = elevation
        if min_elevation is None or elevation < min_elevation:
            min_elevation = elevation

        if prev_elevation is not None:
            delta = elevation - prev_elevation
            if delta > 0:
                total_ascent += delta
            elif delta < 0:
                total_descent += abs(delta)

        prev_elevation = elevation

    if max_elevation is None or min_elevation is None:
        raise GPXProcessingError('Elevation statistics cannot be computed: no elevation data found.')

    elevation_range = max_elevation - min_elevation
    return {
        'total_ascent': round(total_ascent, 2),
        'total_descent': round(total_descent, 2),
        'max_elevation': round(max_elevation, 2),
        'min_elevation': round(min_elevation, 2),
        'elevation_range': round(elevation_range, 2),
    }


def calculate_3d_distance(point1, point2, distance_method: str = 'auto', dataset_size: Optional[int] = None):
    if point1 is point2:
        return 0.0, 'geodesic' if distance_method == 'auto' else distance_method

    if point1.latitude is None or point1.longitude is None:
        raise GPXProcessingError('Point1 has invalid coordinates')
    if point2.latitude is None or point2.longitude is None:
        raise GPXProcessingError('Point2 has invalid coordinates')

    lat1, lon1 = point1.latitude, point1.longitude
    lat2, lon2 = point2.latitude, point2.longitude

    method = distance_method
    if distance_method == 'auto':
        method = 'haversine' if dataset_size and dataset_size > AUTO_METHOD_THRESHOLD else 'geodesic'

    if method == 'geodesic':
        horizontal_distance = geodesic((lat1, lon1), (lat2, lon2)).meters
    elif method == 'haversine':
        lat1_r, lon1_r, lat2_r, lon2_r = map(math.radians, (lat1, lon1, lat2, lon2))
        dlat = lat2_r - lat1_r
        dlon = lon2_r - lon1_r
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        horizontal_distance = EARTH_RADIUS_M * c
    else:
        raise GPXProcessingError("Invalid distance method. Allowed values: 'auto', 'geodesic', 'haversine'.")

    elevation_diff = 0.0
    if point1.elevation is not None and point2.elevation is not None:
        elevation_diff = point2.elevation - point1.elevation

    return math.sqrt(horizontal_distance**2 + elevation_diff**2), method


def create_waypoint(*args):
    if len(args) == 3:
        point, name, description = args
        return gpxpy.gpx.GPXWaypoint(
            latitude=point.latitude,
            longitude=point.longitude,
            elevation=point.elevation,
            name=name,
            description=description,
            time=point.time,
        )

    if len(args) == 5:
        lat, lon, ele, name, description = args
        return gpxpy.gpx.GPXWaypoint(
            latitude=lat,
            longitude=lon,
            elevation=ele,
            name=name,
            description=description,
        )

    raise TypeError(
        'create_waypoint() expected either (point, name, description) or '
        '(lat, lon, ele, name, description)'
    )


def generate_waypoints(points, prefix: str, step_size: float, distance_method: str = 'auto'):
    waypoints = []
    if not points or len(points) < 2:
        return waypoints

    def interpolate_point(p1, p2, fraction):
        lat = p1.latitude + fraction * (p2.latitude - p1.latitude)
        lon = p1.longitude + fraction * (p2.longitude - p1.longitude)
        ele1 = p1.elevation or 0
        ele2 = p2.elevation or 0
        ele = ele1 + fraction * (ele2 - ele1)
        return lat, lon, ele

    start = points[0]
    waypoints.append(create_waypoint(start.latitude, start.longitude, start.elevation, f'{prefix}_TH', 'Trail Head'))

    highest_point = start
    lowest_point = start
    dataset_size = len(points)

    segment_distances = []
    for index in range(1, dataset_size):
        distance, _ = calculate_3d_distance(
            points[index - 1],
            points[index],
            distance_method,
            dataset_size=dataset_size,
        )
        segment_distances.append(distance)

    cumulative_distance = 0.0
    total_distance = sum(segment_distances)
    halfway_distance = total_distance / 2
    step_meters = step_size * 1000
    next_marker_distance = step_meters
    km_index = 1
    halfway_added = False

    for index in range(1, dataset_size):
        p1 = points[index - 1]
        p2 = points[index]
        segment_distance = segment_distances[index - 1]

        if (p2.elevation or 0) > (highest_point.elevation or 0):
            highest_point = p2
        if (p2.elevation or 0) < (lowest_point.elevation or 0):
            lowest_point = p2

        while cumulative_distance + segment_distance >= next_marker_distance:
            distance_into_segment = next_marker_distance - cumulative_distance
            if segment_distance == 0:
                break
            fraction = distance_into_segment / segment_distance
            lat, lon, ele = interpolate_point(p1, p2, fraction)
            waypoints.append(
                create_waypoint(lat, lon, ele, f'{prefix}_KM{km_index:02d}', f'{km_index} km Marker')
            )
            km_index += 1
            next_marker_distance = km_index * step_meters

        if not halfway_added and cumulative_distance + segment_distance >= halfway_distance:
            distance_into_segment = halfway_distance - cumulative_distance
            if segment_distance > 0:
                fraction = distance_into_segment / segment_distance
                lat, lon, ele = interpolate_point(p1, p2, fraction)
                waypoints.append(create_waypoint(lat, lon, ele, f'{prefix}_HLF', 'Halfway Point'))
                halfway_added = True

        cumulative_distance += segment_distance

    end = points[-1]
    waypoints.append(create_waypoint(end.latitude, end.longitude, end.elevation, f'{prefix}_TE', 'Trail End'))
    waypoints.append(
        create_waypoint(
            highest_point.latitude,
            highest_point.longitude,
            highest_point.elevation,
            f'{prefix}_HGH',
            'Highest Point',
        )
    )
    waypoints.append(
        create_waypoint(
            lowest_point.latitude,
            lowest_point.longitude,
            lowest_point.elevation,
            f'{prefix}_LWT',
            'Lowest Point',
        )
    )
    return waypoints


def save_gpx_file(
    original_gpx,
    waypoints,
    output_file: str | Path,
    *,
    creator: str = 'Trail One GPX Trail Waypoint Generator',
    metadata_name: str = 'Trail One - Waypoint-Enriched GPX',
    metadata_desc: str = (
        'GPX trail export generated by Trail One. Includes computed waypoint markers, '
        'preserved route/track geometry, metadata, bounds, and optional extensions.'
    ),
    author_name: str = 'Trail One',
    author_link_href: str = 'https://es.wikiloc.com/wikiloc/user.do?id=18125352',
    author_link_text: str = 'Trail One on Wikiloc',
    author_link_type: str = 'text/html',
    copyright_author: str = 'Trail One | Solo Hiking',
    copyright_year: Optional[int] = None,
    copyright_license: Optional[str] = None,
    metadata_time: Optional[datetime] = None,
    metadata_keywords: Optional[Sequence[str]] = None,
    metadata_extensions: Optional[Iterable[ET.Element]] = None,
    root_extensions: Optional[Iterable[ET.Element]] = None,
    preserve_existing_waypoints: bool = True,
    preserve_existing_routes: bool = True,
    preserve_existing_tracks: bool = True,
    preserve_existing_metadata_extensions: bool = True,
) -> Path:
    def _require_datetime_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _isoformat_z(value: datetime) -> str:
        return _require_datetime_utc(value).isoformat().replace('+00:00', 'Z')

    def _local_name(tag: str) -> str:
        return tag.split('}', 1)[1] if tag.startswith('{') else tag

    def _qname(ns: str, local: str) -> str:
        return f'{{{ns}}}{local}'

    def _append_text(parent: ET.Element, ns: str, tag: str, text: Optional[str]):
        if text is None:
            return None
        text = str(text).strip()
        if not text:
            return None
        child = ET.SubElement(parent, _qname(ns, tag))
        child.text = text
        return child

    def _append_link(parent: ET.Element, ns: str, href: str, text: Optional[str] = None, link_type: Optional[str] = None):
        link_el = ET.SubElement(parent, _qname(ns, 'link'), {'href': href})
        _append_text(link_el, ns, 'text', text)
        _append_text(link_el, ns, 'type', link_type)
        return link_el

    def _iter_point_coords_from_xml(root: ET.Element, ns: str):
        point_tags = ('wpt', 'rtept', 'trkpt')
        for elem in root.iter():
            if _local_name(elem.tag) in point_tags:
                lat = elem.attrib.get('lat')
                lon = elem.attrib.get('lon')
                if lat is None or lon is None:
                    continue
                try:
                    yield float(lat), float(lon)
                except (TypeError, ValueError):
                    continue

    def _iter_point_coords_from_waypoints(items):
        for point in items:
            lat = getattr(point, 'latitude', None)
            lon = getattr(point, 'longitude', None)
            if lat is None or lon is None:
                continue
            if not (-90.0 <= float(lat) <= 90.0):
                continue
            if not (-180.0 <= float(lon) <= 180.0):
                continue
            yield float(lat), float(lon)

    def _compute_bounds(source_root: ET.Element, generated_waypoints, ns: str):
        coords = list(_iter_point_coords_from_xml(source_root, ns))
        coords.extend(_iter_point_coords_from_waypoints(generated_waypoints))
        if not coords:
            return None
        lats = [lat for lat, _ in coords]
        lons = [lon for _, lon in coords]
        return min(lats), min(lons), max(lats), max(lons)

    def _deepcopy_children(parent: Optional[ET.Element]):
        if parent is None:
            return []
        return [copy.deepcopy(child) for child in list(parent)]

    def _serialize_waypoints_to_xml_elements(generated_waypoints, ns: str):
        tmp_gpx = gpxpy.gpx.GPX()
        tmp_gpx.waypoints.extend(generated_waypoints)
        tmp_xml = tmp_gpx.to_xml()
        tmp_root = ET.fromstring(tmp_xml.encode('utf-8'))
        return [copy.deepcopy(elem) for elem in tmp_root.findall(_qname(ns, 'wpt'))]

    def _validate_output_path(path_obj: Path) -> Path:
        if path_obj.exists() and path_obj.is_dir():
            raise GPXProcessingError(f'Output path points to a directory, not a file: {path_obj}')
        if path_obj.suffix.lower() != '.gpx':
            raise GPXProcessingError("Output file must use the '.gpx' extension.")
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        return path_obj.resolve()

    if original_gpx is None:
        raise TypeError('original_gpx must be a parsed GPX object, not None.')
    if not hasattr(original_gpx, 'to_xml'):
        raise TypeError('original_gpx must expose a to_xml() method compatible with gpxpy.GPX.')
    if waypoints is None:
        raise TypeError('waypoints must not be None.')

    output_path = _validate_output_path(Path(output_file))

    for idx, waypoint in enumerate(waypoints):
        if not hasattr(waypoint, 'latitude') or not hasattr(waypoint, 'longitude'):
            raise TypeError(f'Waypoint at index {idx} is not GPX waypoint-compatible.')

    try:
        original_xml = original_gpx.to_xml()
        original_root = ET.fromstring(original_xml.encode('utf-8'))
    except Exception as exc:
        raise GPXProcessingError(f'Unable to serialize/parse original GPX object: {exc}') from exc

    if original_root.tag.startswith('{'):
        gpx_ns = original_root.tag.split('}', 1)[0][1:]
    else:
        gpx_ns = 'http://www.topografix.com/GPX/1/1'

    ET.register_namespace('', gpx_ns)

    now_utc = _require_datetime_utc(metadata_time or datetime.now(timezone.utc))
    year_utc = int(copyright_year or now_utc.year)

    default_keywords = [
        'Trail One', 'Solo Hiking', 'GPX', 'GPX 1.1', 'hiking trail',
        'waypoint generation', 'trailhead', 'trail end', 'halfway point',
        'cumulative distance markers', '3D distance', 'geodesic', 'haversine',
        'elevation', 'route analysis', 'trail navigation', 'outdoor navigation',
        'mountain trail', 'volcanic hiking', 'LCST', 'Nicaragua', 'TrailOne Hiking Series',
    ]
    keywords = list(metadata_keywords) if metadata_keywords else default_keywords
    keywords_text = ', '.join(dict.fromkeys(k.strip() for k in keywords if str(k).strip()))
    bounds = _compute_bounds(original_root, waypoints, gpx_ns)

    final_root = ET.Element(_qname(gpx_ns, 'gpx'), {'version': '1.1', 'creator': creator})
    metadata_el = ET.SubElement(final_root, _qname(gpx_ns, 'metadata'))
    _append_text(metadata_el, gpx_ns, 'name', metadata_name)
    _append_text(metadata_el, gpx_ns, 'desc', metadata_desc)

    author_el = ET.SubElement(metadata_el, _qname(gpx_ns, 'author'))
    _append_text(author_el, gpx_ns, 'name', author_name)
    _append_link(author_el, gpx_ns, author_link_href, author_link_text, author_link_type)

    copyright_el = ET.SubElement(metadata_el, _qname(gpx_ns, 'copyright'), {'author': copyright_author})
    _append_text(copyright_el, gpx_ns, 'year', str(year_utc))
    _append_text(copyright_el, gpx_ns, 'license', copyright_license)
    _append_link(metadata_el, gpx_ns, author_link_href, author_link_text, author_link_type)
    _append_text(metadata_el, gpx_ns, 'time', _isoformat_z(now_utc))
    _append_text(metadata_el, gpx_ns, 'keywords', keywords_text)

    if bounds is not None:
        min_lat, min_lon, max_lat, max_lon = bounds
        ET.SubElement(
            metadata_el,
            _qname(gpx_ns, 'bounds'),
            {
                'minlat': f'{min_lat:.8f}',
                'minlon': f'{min_lon:.8f}',
                'maxlat': f'{max_lat:.8f}',
                'maxlon': f'{max_lon:.8f}',
            },
        )

    existing_metadata = original_root.find(_qname(gpx_ns, 'metadata'))
    existing_metadata_extensions = None
    if existing_metadata is not None:
        existing_metadata_extensions = existing_metadata.find(_qname(gpx_ns, 'extensions'))

    metadata_extension_children = []
    if preserve_existing_metadata_extensions:
        metadata_extension_children.extend(_deepcopy_children(existing_metadata_extensions))
    if metadata_extensions:
        metadata_extension_children.extend(copy.deepcopy(ext) for ext in metadata_extensions)

    if metadata_extension_children:
        metadata_ext_el = ET.SubElement(metadata_el, _qname(gpx_ns, 'extensions'))
        for child in metadata_extension_children:
            metadata_ext_el.append(child)

    if preserve_existing_waypoints:
        for wpt in original_root.findall(_qname(gpx_ns, 'wpt')):
            final_root.append(copy.deepcopy(wpt))

    for generated_wpt in _serialize_waypoints_to_xml_elements(waypoints, gpx_ns):
        final_root.append(generated_wpt)

    if preserve_existing_routes:
        for rte in original_root.findall(_qname(gpx_ns, 'rte')):
            final_root.append(copy.deepcopy(rte))

    if preserve_existing_tracks:
        for trk in original_root.findall(_qname(gpx_ns, 'trk')):
            final_root.append(copy.deepcopy(trk))

    existing_root_extensions = original_root.find(_qname(gpx_ns, 'extensions'))
    root_extension_children = _deepcopy_children(existing_root_extensions)
    if root_extensions:
        root_extension_children.extend(copy.deepcopy(ext) for ext in root_extensions)
    if root_extension_children:
        root_ext_el = ET.SubElement(final_root, _qname(gpx_ns, 'extensions'))
        for child in root_extension_children:
            root_ext_el.append(child)

    try:
        xml_bytes = ET.tostring(final_root, encoding='utf-8', xml_declaration=True)
        ET.fromstring(xml_bytes)
    except Exception as exc:
        raise GPXProcessingError(f'Generated GPX XML is not well-formed: {exc}') from exc

    temp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='wb',
            suffix='.gpx',
            prefix=f'{output_path.stem}.',
            dir=str(output_path.parent),
            delete=False,
        ) as tmp_file:
            temp_path = Path(tmp_file.name)
            tmp_file.write(xml_bytes)
            tmp_file.flush()

        with open(temp_path, 'rb') as file_obj:
            ET.parse(file_obj)

        temp_path.replace(output_path)
    except Exception:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise

    return output_path


def build_enriched_gpx_bytes(original_gpx, waypoints) -> bytes:
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / 'generated_waypoints.gpx'
        save_gpx_file(original_gpx=original_gpx, waypoints=waypoints, output_file=output_path)
        return output_path.read_bytes()


def analyze_gpx(content: bytes, filename: str, max_points: int) -> dict:
    gpx = parse_gpx_bytes(content)
    parsed = parse_gpx_file(gpx, strict=True, max_points=max_points)
    elevation_stats = compute_elevation_statistics(parsed['points'])
    return {
        'gpx': gpx,
        'parsed': parsed,
        'elevation_statistics': elevation_stats,
    }
