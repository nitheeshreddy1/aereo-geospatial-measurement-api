from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.files import router as files_router
from app.core.database import ensure_database_ready
from app.utils.validation import ApiError

app = FastAPI(title="Aereo Geospatial File Measurement API", version="1.0.0")
app.include_router(files_router)


@app.on_event("startup")
def startup_event() -> None:
    ensure_database_ready()


@app.exception_handler(ApiError)
async def api_error_handler(request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.get("/")
def root() -> dict:
    return {"message": "Aereo geospatial file measurement API"}
