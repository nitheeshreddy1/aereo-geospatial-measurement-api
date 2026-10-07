# Architecture Overview

The application follows a layered design to separate HTTP concerns from geospatial processing and persistence.

## Responsibility Split

### API Layer

The API routes live under `app/api/files.py` and expose:

- health and readiness endpoints
- upload endpoint for KML and ZIP archives
- file detail lookup
- measurement retrieval per uploaded file

### Service Layer

`app/services/file_service.py` coordinates the upload lifecycle. It validates file input, creates a record, invokes the geospatial processing pipeline, persists features, and updates the final status.

`app/services/geospatial_service.py` owns the geospatial ingestion logic. It reads KML or extracted Shapefile inputs and converts them to GeoDataFrames.

`app/services/crs_service.py` handles CRS detection and projected measurement transformation.

`app/services/measurement_service.py` calculates the per-feature measurement values.

### Persistence Layer

The database layer is isolated under `app/core/database.py`, `app/models`, and `app/repositories`.

Models include:

- `FileRecord`
- `FeatureRecord`
- `MeasurementRecord`

Repositories wrap SQLAlchemy access for insert/read operations.

### Security and Validation Layer

`app/utils/zip_security.py` validates ZIP integrity and denies extraction paths that traverse outside the safe directory.

`app/utils/validation.py` centralizes filename, size, and API validation rules.

## Runtime Flow

1. Client uploads a file.
2. `FileService.process_upload` validates the request and creates a file record.
3. `GeospatialService.read_geometry_file` reads KML or extracted Shapefile content.
4. `extract_features` checks CRS and converts to measurement CRS.
5. `MeasurementService` computes area or length depending on geometry type.
6. Persisted values are returned via the API response and measurement endpoint.

## Operational Notes

The default database is SQLite for local use, but the model and repository structure are compatible with a Postgres-backed deployment when needed.
