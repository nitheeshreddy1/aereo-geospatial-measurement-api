from __future__ import annotations

from shapely.geometry import GeometryCollection

from app.utils.validation import ApiError


class MeasurementService:
    @staticmethod
    def measurement_for_geometry(geom):
        if geom is None:
            return {"type": "invalid", "value": None, "unit": None, "valid": False, "reason": "Geometry is null."}
        if geom.is_empty:
            return {"type": "invalid", "value": None, "unit": None, "valid": False, "reason": "Geometry is empty."}
        if isinstance(geom, GeometryCollection):
            return None
        if not geom.is_valid:
            return {"type": "invalid", "value": None, "unit": None, "valid": False, "reason": "Geometry is invalid."}

        geometry_type = geom.geom_type
        if geometry_type in {"Polygon", "MultiPolygon"}:
            value = geom.area
            return {"type": "area", "value": round(float(value), 4), "unit": "square_meters", "valid": True}
        if geometry_type in {"LineString", "MultiLineString"}:
            value = geom.length
            return {"type": "length", "value": round(float(value), 4), "unit": "meters", "valid": True}
        if geometry_type in {"Point", "MultiPoint"}:
            return None
        return None

    @staticmethod
    def geometry_to_geojson(geom):
        if geom is None:
            return None
        return geom.__geo_interface__
