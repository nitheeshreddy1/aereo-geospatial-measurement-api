from __future__ import annotations

import math

import geopandas as gpd
from pyproj import CRS

from app.utils.validation import ApiError


class CRSService:
    @staticmethod
    def ensure_source_crs(gdf: gpd.GeoDataFrame) -> str:
        if gdf.crs is None:
            raise ApiError("MISSING_CRS", "The source dataset does not declare a CRS. Upload a file with a valid CRS or provide a projected dataset.", 400)
        try:
            return gdf.crs.to_string()
        except Exception as exc:  # pragma: no cover - defensive guard
            raise ApiError("INVALID_CRS", "The source CRS could not be interpreted.", 400) from exc

    @staticmethod
    def _dataset_bounds(gdf: gpd.GeoDataFrame):
        valid_geometries = gdf.geometry.dropna()
        if valid_geometries.empty:
            raise ApiError("INVALID_CRS", "The source dataset contains no usable geometry for CRS projection.", 400)
        bounds = valid_geometries.total_bounds
        if len(bounds) != 4 or any(not math.isfinite(value) for value in bounds):
            raise ApiError("INVALID_CRS", "The source dataset bounds are invalid for CRS selection.", 400)
        return bounds

    @staticmethod
    def _is_dataset_antarctic_or_polar(bounds) -> bool:
        _, _, min_y, max_y = bounds
        return min_y < -80 or max_y > 84

    @staticmethod
    def _spans_multiple_utm_zones(bounds) -> bool:
        min_x, max_x, _, _ = bounds
        lon_range = max_x - min_x
        # If the dataset covers more than one standard UTM zone, it cannot be safely represented by a single local UTM CRS.
        return lon_range > 6

    @staticmethod
    def choose_measurement_crs(gdf: gpd.GeoDataFrame) -> str:
        source_crs = CRSService.ensure_source_crs(gdf)
        crs = CRS.from_user_input(source_crs)
        if crs.is_projected:
            return crs.to_string()

        if not crs.is_geographic:
            raise ApiError("INVALID_CRS", "The dataset CRS is not a supported projected or geographic CRS.", 400)

        bounds = CRSService._dataset_bounds(gdf)
        _, max_x, min_y, max_y = bounds
        if CRSService._is_dataset_antarctic_or_polar(bounds):
            raise ApiError("UNSAFE_CRS_SELECTION", "The dataset is too close to the poles for a safe automatic UTM projection. Supply a projected CRS explicitly.", 400)

        if CRSService._spans_multiple_utm_zones(bounds):
            raise ApiError("UNSAFE_CRS_SELECTION", "The dataset spans multiple UTM zones; automatic measurement is unsafe. Supply a projected CRS explicitly.", 400)

        valid_geometries = gdf.geometry.dropna()
        centroid = valid_geometries.unary_union.centroid
        lon = centroid.x
        lat = centroid.y
        if not math.isfinite(lon) or not math.isfinite(lat):
            raise ApiError("INVALID_CRS", "The geographic extent is invalid for local projection selection.", 400)

        if min_y < -80 or max_y > 84:
            raise ApiError("UNSAFE_CRS_SELECTION", "The dataset falls into a polar region that is unsafe for automatic UTM projection.", 400)

        if lon < -180 or lon > 180 or max_x > 180 or min_y < -90 or max_y > 90:
            raise ApiError("INVALID_CRS", "The geographic coordinates are outside valid world bounds.", 400)

        zone = int((lon + 180) / 6) + 1
        if lat >= 0:
            epsg = 32600 + zone
        else:
            epsg = 32700 + zone
        return f"EPSG:{epsg}"

    @staticmethod
    def transform_geodata(gdf: gpd.GeoDataFrame, measurement_crs: str) -> gpd.GeoDataFrame:
        try:
            return gdf.to_crs(measurement_crs)
        except Exception as exc:
            raise ApiError("INVALID_CRS", "Unable to transform the dataset to the selected measurement CRS.", 400) from exc
