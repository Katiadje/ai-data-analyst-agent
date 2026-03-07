"""File upload endpoint."""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status

from api.models import UploadResponse

router = APIRouter()

UPLOADS_DIR = os.environ.get("UPLOADS_DIR", "/tmp/ai_analyst_uploads")
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", "50"))

os.makedirs(UPLOADS_DIR, exist_ok=True)


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a CSV or Excel dataset",
)
async def upload_file(file: UploadFile) -> UploadResponse:
    # Validate extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type '{suffix}' not supported. Use: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read content
    content = await file.read()
    size_bytes = len(content)

    if size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({size_bytes // 1024 // 1024} MB). Max: {MAX_FILE_SIZE_MB} MB",
        )

    if size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Empty file.",
        )

    # Save file
    session_id = uuid.uuid4().hex
    dest = os.path.join(UPLOADS_DIR, f"{session_id}{suffix}")
    with open(dest, "wb") as f:
        f.write(content)

    return UploadResponse(
        session_id=session_id,
        filename=file.filename or "unknown",
        file_path=dest,
        size_bytes=size_bytes,
    )
