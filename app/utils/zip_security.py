import io
import zipfile
from pathlib import Path

from app.core.config import settings
from app.utils.validation import ApiError, sanitize_archive_member


def safe_extract_zip(zip_source, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    try:
        if isinstance(zip_source, (str, Path)):
            zip_path = Path(zip_source)
            if not zip_path.exists():
                raise ApiError("INVALID_ZIP", "The uploaded ZIP archive could not be found on disk.", 400)
            archive = zipfile.ZipFile(zip_path)
        else:
            archive = zipfile.ZipFile(io.BytesIO(zip_source))

        with archive:
            infos = archive.infolist()
            if not infos:
                raise ApiError("INVALID_ZIP", "The uploaded ZIP archive is empty.", 400)
            if len(infos) > settings.MAX_ZIP_ENTRIES:
                raise ApiError("INVALID_ZIP", "The ZIP archive contains too many members.", 400)

            total_uncompressed = 0
            safe_members = []
            for info in infos:
                if info.is_dir():
                    continue
                if info.file_size > settings.MAX_ZIP_MEMBER_SIZE_BYTES:
                    raise ApiError("ZIP_MEMBER_TOO_LARGE", "A ZIP member exceeds the configured maximum size.", 400)
                total_uncompressed += info.file_size
                if total_uncompressed > settings.MAX_ZIP_TOTAL_SIZE_BYTES:
                    raise ApiError("ZIP_TOO_LARGE", "The extracted ZIP content exceeds the configured size limit.", 400)
                if info.compress_size and info.compress_size > 0:
                    ratio = info.file_size / info.compress_size
                    if ratio > settings.MAX_ZIP_COMPRESSION_RATIO:
                        raise ApiError("ZIP_BOMB", "The ZIP archive has an unsafe compression ratio.", 400)

                safe_name = sanitize_archive_member(info.filename)
                target_path = destination_dir / safe_name
                target_path.parent.mkdir(parents=True, exist_ok=True)
                if not str(target_path.resolve()).startswith(str(destination_dir.resolve())):
                    raise ApiError("INVALID_ZIP", "ZIP entry escapes the extraction directory.", 400)
                with archive.open(info, "r") as source, open(target_path, "wb") as sink:
                    sink.write(source.read())
                safe_members.append(safe_name)
    except zipfile.BadZipFile as exc:
        raise ApiError("INVALID_ZIP", "The uploaded ZIP archive is malformed or corrupted.", 400) from exc

    shapefiles = sorted(name for name in safe_members if name.lower().endswith(".shp"))
    if not shapefiles:
        raise ApiError("MISSING_SHAPEFILE", "The ZIP does not contain a valid Shapefile dataset.", 400)
    if len(shapefiles) > 1:
        raise ApiError("MISSING_SHAPEFILE", "The ZIP contains multiple Shapefile datasets and is ambiguous.", 400)

    shp_name = shapefiles[0]
    shp_path = destination_dir / shp_name
    base_name = shp_path.stem.lower()
    required_extensions = (".dbf", ".shx")
    for required in required_extensions:
        companion = shp_path.with_suffix(required)
        if not companion.exists():
            raise ApiError("MISSING_SHAPEFILE", f"The ZIP is missing the required {required} companion file.", 400)

    mismatched = []
    for member in safe_members:
        member_path = Path(member)
        if member_path.name.lower().startswith(base_name + "."):
            continue
        if member_path.suffix.lower() in {".dbf", ".shx", ".prj", ".qix", ".sbn", ".sbx", ".shp"}:
            mismatched.append(member)
    if mismatched:
        raise ApiError("MISSING_SHAPEFILE", "The ZIP contains mismatched shapefile companion files.", 400)

    return shp_path
