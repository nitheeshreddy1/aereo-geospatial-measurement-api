# Design Decisions and Rationale

## Why the project uses FastAPI

FastAPI provides a lightweight but production-friendly way to expose a clear API contract, automatic OpenAPI documentation, and efficient async-friendly request handling without much boilerplate.

## Why GeoPandas and Shapely

The assignment requires geospatial parsing and geometry operations. GeoPandas handles dataset reading and attribute extraction, while Shapely provides the geometry primitives and measurement operations needed for polygon area and line length calculations.

## Why CRS projection is required

Distance and area calculations from EPSG:4326 in degrees are mathematically invalid for metric output. The service therefore detects geographic coordinate reference systems and reprojects to a local metric CRS before computing values.

## Why ZIP validation is strict

Shapefile uploads are usually delivered as a set of companion files: `.shp`, `.dbf`, `.shx`, and sometimes `.prj`. The service validates both the archive structure and the required sidecar files so malformed or malicious ZIP payloads fail cleanly.

## Why unsupported geometries are not fatal

The API needs to continue responding gracefully when it encounters geometry types that do not have a meaningful measurement. The implementation keeps the feature record and marks the measurement as `null` instead of rejecting the entire upload.

## Why SQLite is the default

The project is designed as a backend exercise and developer-friendly prototype. SQLite minimizes setup friction while still demonstrating durable persistence and realistic API behavior.

## Why the architecture is layered

This project separates request handling, business logic, data access, and geospatial computations. That separation makes testing easier and keeps the system maintainable as additional geospatial formats or persistence layers are added.
