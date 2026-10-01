from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from dependencies.auth import get_current_user
from dfs.contest_rules import UnsupportedContest
from dfs.dk_parser import DKParseError
from dfs.optimizer import OptimizerError
from services.dfs_services import analyze_slate
from services.storage_service import upload_lineup_file


router = APIRouter(
    prefix="/lineups",
    tags=["lineups"],
)

MAX_UPLOAD_BYTES = 2 * 1024 * 1024


def _uid(user: dict) -> str:
    """
    Get the authenticated Supabase user ID.

    The ID comes from the validated Bearer token through
    get_current_user(). It must never come from the request body,
    query parameters, or uploaded file.
    """
    if not isinstance(user, dict):
        raise HTTPException(
            status_code=401,
            detail="Invalid authenticated user.",
        )

    user_id = user.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user ID not found.",
        )

    return str(user_id)


async def _read_csv_upload(file: UploadFile) -> tuple[str, bytes]:
    """
    Validate and read a DraftKings CSV upload.

    Returns:
        (safe_filename, file_content)
    """
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A file is required.",
        )

    # Only use the filename itself, never a client-provided directory.
    safe_filename = Path(file.filename).name

    if not safe_filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File is too large. Maximum size is 2 MB.",
        )

    return safe_filename, content


def _storage_path(
    user_id: str,
    file_id: str,
    filename: str,
) -> str:
    """
    Build a user-isolated storage path.

    Every uploaded file lives under the authenticated user's directory.
    """
    return f"{user_id}/{file_id}/{filename}"


def _store_file(
    storage_path: str,
    content: bytes,
) -> None:
    """Store a file without exposing internal storage errors."""
    try:
        upload_lineup_file(
            storage_path,
            content,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to store the uploaded file.",
        ) from exc


@router.post("/upload")
async def upload_lineup_file_endpoint(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    Upload a DraftKings CSV and store it in Supabase Storage.

    The storage path is isolated by authenticated user ID.
    """
    user_id = _uid(user)

    filename, content = await _read_csv_upload(file)

    file_id = str(uuid4())

    storage_path = _storage_path(
        user_id,
        file_id,
        filename,
    )

    _store_file(
        storage_path,
        content,
    )

    return {
        "success": True,
        "file_id": file_id,
        "filename": filename,
        "storage_path": storage_path,
        "message": "File uploaded and stored successfully.",
    }


@router.post("/analyze")
async def analyze_lineup_file(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    Analyze a DraftKings CSV and store the original file.

    The uploaded file is private to the authenticated user through
    its user-scoped storage path.
    """
    user_id = _uid(user)

    filename, content = await _read_csv_upload(file)

    file_id = str(uuid4())

    storage_path = _storage_path(
        user_id,
        file_id,
        filename,
    )

    _store_file(
        storage_path,
        content,
    )

    try:
        result = analyze_slate(content)

    except (
        DKParseError,
        UnsupportedContest,
        OptimizerError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze the lineup file.",
        ) from exc

    return {
        "success": True,
        "file_id": file_id,
        "filename": filename,
        "storage_path": storage_path,
        "analysis": result,
    }


@router.get("/health")
async def lineup_health():
    """
    Public service health check.

    This endpoint does not expose user data.
    """
    return {
        "status": "ok",
        "service": "lineups",
    }