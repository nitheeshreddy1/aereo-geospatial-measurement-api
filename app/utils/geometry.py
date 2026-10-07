from __future__ import annotations

from shapely import force_2d


def normalize_geometry_for_storage(geom):
    """Strip elevation while preserving the XY footprint for PostGIS storage.

    This assignment requires 2D measurement and storage for area/length. Elevation
    is retained in source metadata when needed for parsing, but the persisted
    PostGIS geometry is normalized to 2D to avoid "Geometry has Z dimension but
    column does not" errors and to keep measurements aligned with the 2D schema.
    """
    if geom is None:
        return None
    if getattr(geom, "is_empty", False):
        return geom
    try:
        return force_2d(geom)
    except Exception:
        return geom
