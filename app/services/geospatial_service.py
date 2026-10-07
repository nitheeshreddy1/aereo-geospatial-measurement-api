from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import GeometryCollection

from app.services.crs_service import CRSService
from app.services.measurement_service import MeasurementService
from app.utils.validation import ApiError
from app.utils.zip_security import safe_extract_zip


class GeospatialService:
    @staticmethod
    def _sanitize_property_value(value):
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                return None
            return value
        if isinstance(value, dict):
            return {str(key): GeospatialService._sanitize_property_value(val) for key, val in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [GeospatialService._sanitize_property_value(item) for item in value]
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        if pd.isna(value):
            return None
        if hasattr(value, "item"):
            try:
                item = value.item()
                return GeospatialService._sanitize_property_value(item)
            except ValueError:
                pass
        try:
            import json
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            return str(value)

    def __init__(self):
        self.crs_service = CRSService()
        self.measurement_service = MeasurementService()

    def read_geometry_file(self, filename: str, file_source):
        suffix = os.path.splitext(filename)[1].lower()
        temp_dir = tempfile.mkdtemp(prefix="aereo_")
        try:
            try:
                if suffix == ".kml":
                    temp_path = Path(temp_dir) / filename
                    if hasattr(file_source, "read"):
                        with open(temp_path, "wb") as sink:
                            for chunk in iter(lambda: file_source.read(65536), b""):
                                sink.write(chunk)
                    elif isinstance(file_source, (str, os.PathLike)):
                        source_path = Path(file_source)
                        if source_path.exists() and source_path.is_file():
                            temp_path.write_bytes(source_path.read_bytes())
                        else:
                            raise ApiError("CORRUPTED_GEOSPATIAL_FILE", "The uploaded geospatial file could not be parsed as valid geospatial data.", 400)
                    elif isinstance(file_source, (bytes, bytearray)):
                        temp_path.write_bytes(file_source)
                    else:
                        raise ApiError("CORRUPTED_GEOSPATIAL_FILE", "The uploaded geospatial file could not be parsed as valid geospatial data.", 400)
                    gdf = gpd.read_file(temp_path)
                elif suffix == ".zip":
                    extracted_dir = Path(temp_dir) / "archive"
                    shapefile_path = safe_extract_zip(file_source, extracted_dir)
                    gdf = gpd.read_file(shapefile_path)
                else:
                    raise ApiError("UNSUPPORTED_FILE_TYPE", "Unsupported geospatial file type.", 400)
            except Exception as exc:
                if isinstance(exc, ApiError):
                    raise
                raise ApiError("CORRUPTED_GEOSPATIAL_FILE", "The uploaded geospatial file could not be parsed as valid geospatial data.", 400) from exc

            if gdf.empty:
                raise ApiError("CORRUPTED_GEOSPATIAL_FILE", "The uploaded geospatial file contains no features.", 400)
            return gdf
        finally:
            for item in Path(temp_dir).glob("**/*"):
                if item.is_file() and item.exists():
                    try:
                        item.unlink()
                    except OSError:
                        pass
            try:
                Path(temp_dir).rmdir()
            except OSError:
                pass

    def extract_features(self, gdf: gpd.GeoDataFrame):
        source_crs = self.crs_service.ensure_source_crs(gdf)
        measurement_crs = self.crs_service.choose_measurement_crs(gdf)
        transformed = self.crs_service.transform_geodata(gdf, measurement_crs)

        features = []
        for feature_index, row in transformed.iterrows():
            geom = row.geometry
            measurement = None
            invalid_reason = None
            geometry_type = "Unknown"

            if geom is None:
                invalid_reason = "Geometry is null."
            elif geom.is_empty:
                invalid_reason = "Geometry is empty."
            else:
                geometry_type = geom.geom_type
                if isinstance(geom, GeometryCollection):
                    measurement = None
                elif not geom.is_valid:
                    invalid_reason = "Geometry is invalid."
                    measurement = {"type": "invalid", "value": None, "unit": None, "valid": False, "reason": invalid_reason}
                else:
                    measurement = self.measurement_service.measurement_for_geometry(geom)

            properties = {
                str(key): self._sanitize_property_value(value)
                for key, value in row.items()
                if key != transformed.geometry.name
            }
            if invalid_reason is not None:
                properties["_invalid_reason"] = invalid_reason
            geojson = self.measurement_service.geometry_to_geojson(geom)
            source_geometry = self.measurement_service.geometry_to_geojson(row.geometry)
            features.append(
                {
                    "feature_id": int(feature_index),
                    "geometry_type": geometry_type,
                    "geometry": geojson,
                    "source_geometry": source_geometry,
                    "properties": properties,
                    "measurement": measurement,
                    "source_crs": source_crs,
                    "measurement_crs": measurement_crs,
                }
            )
        return features, source_crs, measurement_crs
