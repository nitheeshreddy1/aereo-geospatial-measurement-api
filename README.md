# Aereo Geospatial File Measurement API

A FastAPI service for ingesting geospatial uploads and computing measurement values for supported geometry types. It accepts KML files and ZIP archives containing a Shapefile and returns metadata, geometry details, and per-feature measurements.

## Why PostgreSQL + PostGIS

This project uses PostgreSQL with PostGIS as the production-style database because geospatial data needs spatial indexing, geometry storage, and DB-level compatibility with geographic processing in a real deployment environment. PostGIS is the standard choice for robust geospatial persistence and is the correct foundation for a service that stores geometry, CRS metadata, and measurement results.

## Features

- Upload KML or zipped Shapefile datasets
- Extract per-feature metadata: feature index, geometry type, geometry, CRS, and attributes
- Measure polygons by area, lines by length, and leave point features without a required measurement
- Reject malformed or unsafe archives without crashing the service
- Persist upload metadata and feature results in PostgreSQL/PostGIS
- Provide API endpoints for upload status and measurement retrieval

## Tech Stack

- FastAPI
- SQLAlchemy
- PostgreSQL + PostGIS
- Alembic
- GeoPandas
- Shapely
- PyProj
- Fiona

## Database schema

The database contains the following core tables:

- `files`: upload metadata, source CRS, measurement CRS, status, timestamps, and processing state
- `features`: one row per uploaded feature, with JSON attribute payloads and a PostGIS geometry column for spatial persistence
- `measurements`: computed measurement metadata for each feature, including type, value, and unit

Relationships:

- One `file` can have many `features`
- One `feature` can have many `measurements`
- Foreign keys and uniqueness constraints are used for consistent data integrity

## Environment variables

Copy the example environment file and adjust values for your local or Docker setup:

```bash
copy .env.example .env
```

Key variables:

- `DATABASE_URL` – PostgreSQL connection string for the application
- `POSTGRES_DB` – database name
- `POSTGRES_USER` – database user
- `POSTGRES_PASSWORD` – database password
- `MAX_UPLOAD_SIZE_BYTES` – upload size limit
- `DB_ECHO` – SQL echo toggle for local debugging

## Local setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   ```bash
   copy .env.example .env
   ```
4. Start PostgreSQL + PostGIS locally or via Docker Compose.
5. Run Alembic migrations:
   ```bash
   alembic upgrade head
   ```
6. Start the API:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Docker setup

The project ships with a Docker Compose setup that starts:

- `db`: PostgreSQL + PostGIS
- `api`: FastAPI application

```bash
docker compose up --build
```

The Compose stack:

- exposes PostgreSQL on port `5432`
- exposes the API on port `8000`
- uses a managed database volume for persistence
- waits for PostgreSQL health before starting the API
- runs Alembic migrations during startup

## Database migrations

The project uses Alembic for the production schema. The application does not rely on `Base.metadata.create_all()` for PostgreSQL in production.

To apply migrations:

```bash
alembic upgrade head
```

## Testing

The existing test suite remains the primary validation path for API behavior. The application can still be used with SQLite for local lightweight testing if needed, but the project is designed around PostgreSQL + PostGIS as the production database.

```bash
pytest -q
```

## API Endpoints

### Health checks

- GET /health
- GET /ready

### Upload and file metadata

- POST /api/files/
- GET /api/files/{id}/

### Measurements

- GET /api/files/{id}/measurements/

Example upload:

```bash
curl -X POST "http://localhost:8000/api/files/" \
  -F "file=@sample.kml"
```

Example measurement fetch:

```bash
curl "http://localhost:8000/api/files/{id}/measurements/"
```

## File Processing Flow

1. A client uploads a `.kml` or `.zip` file.
2. The request is validated for file type, size, and archive integrity.
3. For ZIP archives, the service validates that the archive contains a real Shapefile dataset and prevents traversal or malicious extraction paths.
4. GeoPandas reads the dataset and exposes each feature row.
5. The service normalizes geometry and attributes into a consistent internal payload.
6. Measurements are computed only for supported geometric shapes.
7. Results are stored in the database and returned through the API.

## Measurement Calculation Flow

- Polygon or MultiPolygon: area in square meters
- LineString or MultiLineString: length in meters
- Point: no numeric measurement required
- Unsupported geometry types: returned as structured feature data without crashing the request

## CRS Handling

A major requirement of the service is to avoid using geographic CRS values like EPSG:4326 directly for distance and area calculations. The flow is:

1. Detect the source CRS from the file metadata or dataset.
2. If the source is geographic, choose a local projected CRS (for example UTM or an equivalent local metric projection).
3. Reproject the geometry before running area or length calculations.
4. Store both the original source CRS and the measurement CRS in the upload record.

This keeps area and distance results in metres instead of degrees and prevents invalid geometry measurements.

## Architecture

The service is split into a few clearly separated layers:

- `app.api`: HTTP routes and response shaping
- `app.services`: upload processing, geospatial parsing, CRS logic, and measurement orchestration
- `app.repositories`: data access for files, features, and measurements
- `app.models`: SQLAlchemy models for persisted state
- `app.schemas`: request/response contracts
- `app.utils`: validation and ZIP security helpers

## Design Decisions

- PostgreSQL + PostGIS is the production-style database for real geospatial persistence.
- The application uses a layered service architecture to keep geospatial logic independent from the API layer.
- ZIP archive validation blocks path traversal and ensures the archive includes required Shapefile companion files.
- Metadata is preserved alongside geometry and measurement outputs so the API remains auditable.

## Learning and Future Scope

This project is intentionally structured to be a strong foundation for production extensions:

- add heavier spatial observability and monitoring
- add background job processing for large uploads
- add pagination and bulk retrieval for large results
- expand geospatial format coverage and validation rules

## Security

The service is designed to be safe for local and containerized deployment:

- environment secrets are kept in `.env` and never committed
- ZIP archives are validated before extraction to prevent traversal and malformed payloads
- file type and size limits are enforced before processing
- geospatial validation is performed before measurement and database persistence

## GitHub / Deployment Notes

The project is ready to be pushed to GitHub without secrets or private infrastructure dependencies. The Docker Compose setup provides an example deployment path for local or shared environment use.
