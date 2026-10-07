from pathlib import Path
import io
import json
import zipfile

import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point, MultiPolygon, MultiLineString

from app.utils.geometry import normalize_geometry_for_storage

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _make_kml(contents: str) -> bytes:
    return contents.encode("utf-8")


def _make_polygon_kml() -> bytes:
    return _make_kml(
        '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Square</name>
      <ExtendedData>
        <Data name="name"><value>Area1</value></Data>
      </ExtendedData>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              0,0,0 0,1,0 1,1,0 1,0,0 0,0,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
'''
    )


def _make_line_kml() -> bytes:
    return _make_kml(
        '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Line</name>
      <LineString>
        <coordinates>
          0,0,0 0,1,0 1,1,0
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>
'''
    )


def _make_point_kml() -> bytes:
    return _make_kml(
        '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <Point>
        <coordinates>1,2,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>
'''
    )


def _zip_shapefile_dataset(base_path: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(base_path.iterdir()):
            zf.write(p, arcname=f"{base_path.name}/{p.name}")


def _make_polygon_shapefile_zip(tmp_path: Path, *, has_prj: bool = True, bad_name: bool = False):
    polygon = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    gdf = gpd.GeoDataFrame({"name": ["area"], "id": [1]}, geometry=[polygon], crs="EPSG:4326")
    base_path = tmp_path / ("bad" if bad_name else "sample")
    gdf.to_file(base_path, driver="ESRI Shapefile")

    if not has_prj:
        prj_path = base_path / f"{base_path.name}.prj"
        if prj_path.exists():
            prj_path.unlink()

    zip_path = tmp_path / "sample.zip"
    _zip_shapefile_dataset(base_path, zip_path)
    return zip_path.read_bytes()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_valid_kml_upload():
    response = client.post(
        "/api/files/",
        files={"file": ("sample.kml", _make_polygon_kml(), "application/vnd.google-earth.kml+xml")},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["filename"] == "sample.kml"
    assert payload["feature_count"] == 1
    assert payload["status"] == "COMPLETED"
    assert payload["source_crs"] == "EPSG:4326"


def test_valid_zipped_shapefile_upload(tmp_path):
    zip_bytes = _make_polygon_shapefile_zip(tmp_path)
    response = client.post(
        "/api/files/",
        files={"file": ("sample.zip", zip_bytes, "application/zip")},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["filename"] == "sample.zip"
    assert payload["feature_count"] == 1
    assert payload["status"] == "COMPLETED"


def test_invalid_extension():
    response = client.post(
        "/api/files/",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400
    assert "UNSUPPORTED_FILE_TYPE" in response.text


def test_empty_upload():
    response = client.post(
        "/api/files/",
        files={"file": ("empty.kml", b"", "application/vnd.google-earth.kml+xml")},
    )
    assert response.status_code == 400


def test_oversized_file(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "MAX_UPLOAD_SIZE_BYTES", 10)
    response = client.post(
        "/api/files/",
        files={"file": ("big.kml", b"x" * 100, "application/vnd.google-earth.kml+xml")},
    )
    assert response.status_code == 413


def test_invalid_kml():
    response = client.post(
        "/api/files/",
        files={"file": ("broken.kml", b"not a real kml", "application/vnd.google-earth.kml+xml")},
    )
    assert response.status_code == 400


def test_invalid_zip():
    bad_zip = b"not a valid zip archive"
    response = client.post(
        "/api/files/",
        files={"file": ("broken.zip", bad_zip, "application/zip")},
    )
    assert response.status_code == 400
    assert "INVALID_ZIP" in response.text


def test_zip_path_traversal(tmp_path):
    zip_path = tmp_path / "evil.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("../../evil.txt", "nope")
    response = client.post(
        "/api/files/",
        files={"file": ("evil.zip", zip_path.read_bytes(), "application/zip")},
    )
    assert response.status_code == 400
    assert "INVALID_ZIP" in response.text or "MISSING_SHAPEFILE" in response.text


def test_zip_missing_shapefile(tmp_path):
    zip_path = tmp_path / "missing.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("notes.txt", "not a shapefile")
    response = client.post(
        "/api/files/",
        files={"file": ("missing.zip", zip_path.read_bytes(), "application/zip")},
    )
    assert response.status_code == 400
    assert "MISSING_SHAPEFILE" in response.text


def test_polygon_area():
    response = client.post(
        "/api/files/",
        files={"file": ("poly.kml", _make_polygon_kml(), "application/vnd.google-earth.kml+xml")},
    )

    file_id = response.json()["id"]
    measurements = client.get(f"/api/files/{file_id}/measurements/")
    assert measurements.status_code == 200
    data = measurements.json()
    assert data["file_id"] == file_id
    assert data["measurements"][0]["measurement"]["type"] == "area"
    assert data["measurements"][0]["measurement"]["unit"] == "square_meters"
    assert data["measurements"][0]["measurement"]["value"] > 0


def test_mult_polygon_area(tmp_path):
    polygon1 = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    polygon2 = Polygon([(10, 10), (10, 11), (11, 11), (11, 10), (10, 10)])
    gdf = gpd.GeoDataFrame({"name": ["poly1", "poly2"]}, geometry=[polygon1, polygon2], crs="EPSG:4326")
    path = tmp_path / "multi"
    gdf.to_file(path, driver="ESRI Shapefile")
    zip_path = tmp_path / "multi.zip"
    _zip_shapefile_dataset(tmp_path / "multi", zip_path)
    response = client.post(
        "/api/files/",
        files={"file": ("multi.zip", zip_path.read_bytes(), "application/zip")},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["feature_count"] == 2


def test_line_length():
    response = client.post(
        "/api/files/",
        files={"file": ("line.kml", _make_line_kml(), "application/vnd.google-earth.kml+xml")},
    )
    file_id = response.json()["id"]
    measurements = client.get(f"/api/files/{file_id}/measurements/")
    data = measurements.json()
    assert data["measurements"][0]["measurement"]["type"] == "length"
    assert data["measurements"][0]["measurement"]["unit"] == "meters"
    assert data["measurements"][0]["measurement"]["value"] > 0


def test_point_without_measurement():
    response = client.post(
        "/api/files/",
        files={"file": ("point.kml", _make_point_kml(), "application/vnd.google-earth.kml+xml")},
    )
    file_id = response.json()["id"]
    measurements = client.get(f"/api/files/{file_id}/measurements/")
    data = measurements.json()
    assert data["measurements"][0]["measurement"] is None


def test_unsupported_geometry():
    kml = _make_kml(
        '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Placemark>
    <MultiGeometry>
      <Point><coordinates>0,0,0</coordinates></Point>
      <LineString><coordinates>0,0,0 1,1,0</coordinates></LineString>
    </MultiGeometry>
  </Placemark>
</kml>
'''
    )
    response = client.post(
        "/api/files/",
        files={"file": ("unsupported.kml", kml, "application/vnd.google-earth.kml+xml")},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["feature_count"] == 1


def test_invalid_geometry_is_safe(tmp_path):
    bad_polygon = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    gdf = gpd.GeoDataFrame({"name": ["bad"]}, geometry=[bad_polygon], crs="EPSG:4326")
    base_path = tmp_path / "invalid_geometry"
    gdf.to_file(base_path, driver="ESRI Shapefile")
    zip_path = tmp_path / "invalid_geometry.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(base_path.iterdir()):
            if p.name == zip_path.name:
                continue
            zf.write(p, arcname=p.name)
    response = client.post(
        "/api/files/",
        files={"file": ("invalid_geometry.zip", zip_path.read_bytes(), "application/zip")},
    )
    assert response.status_code == 200, response.text
    file_id = response.json()["id"]
    payload = client.get(f"/api/files/{file_id}/measurements/").json()
    assert payload["measurements"][0]["measurement"]["valid"] is False


def test_epsg_4326_transformation():
    response = client.post(
        "/api/files/",
        files={"file": ("poly.kml", _make_polygon_kml(), "application/vnd.google-earth.kml+xml")},
    )
    file_data = client.get(f"/api/files/{response.json()['id']}/")
    assert file_data.status_code == 200
    assert file_data.json()["source_crs"] == "EPSG:4326"
    assert file_data.json()["measurement_crs"] is not None
    assert file_data.json()["measurement_crs"] != "EPSG:4326"


def test_projected_crs_input(tmp_path):
    polygon = Polygon([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)])
    gdf = gpd.GeoDataFrame({"name": ["proj"]}, geometry=[polygon], crs="EPSG:3857")
    path = tmp_path / "proj"
    gdf.to_file(path, driver="ESRI Shapefile")
    zip_path = tmp_path / "proj.zip"
    _zip_shapefile_dataset(tmp_path / "proj", zip_path)
    response = client.post(
        "/api/files/",
        files={"file": ("proj.zip", zip_path.read_bytes(), "application/zip")},
    )
    assert response.status_code == 200
    file_id = response.json()["id"]
    payload = client.get(f"/api/files/{file_id}/measurements/").json()
    assert payload["measurements"][0]["measurement"]["unit"] == "square_meters"


def test_missing_crs(tmp_path):
    polygon = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    gdf = gpd.GeoDataFrame({"name": ["nocrs"]}, geometry=[polygon])
    path = tmp_path / "nocrs"
    gdf.to_file(path, driver="ESRI Shapefile")
    zip_path = tmp_path / "nocrs.zip"
    _zip_shapefile_dataset(tmp_path / "nocrs", zip_path)
    response = client.post(
        "/api/files/",
        files={"file": ("nocrs.zip", zip_path.read_bytes(), "application/zip")},
    )
    assert response.status_code in {400, 422}


def test_missing_file_id():
    response = client.get("/api/files/not-real-id/")
    assert response.status_code == 404


def test_database_persistence():
    response = client.post(
        "/api/files/",
        files={"file": ("sample.kml", _make_polygon_kml(), "application/vnd.google-earth.kml+xml")},
    )
    assert response.status_code == 200
    file_id = response.json()["id"]
    record = client.get(f"/api/files/{file_id}/")
    assert record.status_code == 200
    payload = record.json()
    assert payload["id"] == file_id
    assert payload["status"] == "COMPLETED"


def test_normalize_geometry_for_storage_removes_z_from_supported_geometries():
    polygon_3d = Polygon([(0, 0, 0), (0, 1, 2), (1, 1, 3), (1, 0, 1), (0, 0, 0)])
    line_3d = LineString([(0, 0, 0), (1, 1, 2), (2, 1, 3)])
    point_3d = Point(1, 2, 3)
    multipolygon_3d = MultiPolygon([
        Polygon([(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)]),
        Polygon([(10, 10, 0), (10, 11, 0), (11, 11, 0), (11, 10, 0), (10, 10, 0)]),
    ])

    for original, expected_type in [(polygon_3d, "Polygon"), (line_3d, "LineString"), (point_3d, "Point"), (multipolygon_3d, "MultiPolygon")]:
        normalized = normalize_geometry_for_storage(original)
        assert normalized is not None
        assert normalized.geom_type == expected_type
        assert not normalized.has_z
        assert original.has_z is True

    polygon_2d = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    normalized_2d = normalize_geometry_for_storage(polygon_2d)
    assert normalized_2d.equals_exact(polygon_2d, tolerance=1e-9)
    assert not normalized_2d.has_z


def test_3d_kml_upload_persists_as_2d_geometry():
    payload = _make_kml(
        '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Cube</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              0,0,10 0,1,10 1,1,10 1,0,10 0,0,10
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
'''
    )
    response = client.post(
        "/api/files/",
        files={"file": ("three_d_polygon.kml", payload, "application/vnd.google-earth.kml+xml")},
    )
    assert response.status_code == 200, response.text
    file_id = response.json()["id"]
    assert client.get(f"/api/files/{file_id}/measurements/").status_code == 200


def test_api_response_validation():
    response = client.post(
        "/api/files/",
        files={"file": ("sample.kml", _make_polygon_kml(), "application/vnd.google-earth.kml+xml")},
    )
    payload = response.json()
    assert set(payload.keys()) >= {"id", "filename", "feature_count", "status", "source_crs", "measurement_crs"}
