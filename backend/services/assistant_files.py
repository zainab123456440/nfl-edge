"""
services/assistant_files.py

File handling for the AI assistant.

  * register_uploaded_file  - the browser uploads straight to Supabase Storage
                              (avoids the ~4.5 MB request-body limit on Vercel),
                              then calls the backend to read + index the file
  * extract_text            - PDF, DOCX, XLSX, CSV, TXT, JSON, ... -> plain text
  * create_generated_file   - files the assistant creates for the user to download
  * signed_download_url, list_files, get_file, delete_file, load_attachments

Security model
  - Database access uses the USER-SCOPED client, so row-level security applies.
  - Storage access uses the service client, but every path is checked to start
    with "<user_id>/" before it is touched.
"""

from __future__ import annotations

import base64
import csv
import io
import re
import uuid
from typing import Any

from config.settings import settings
from config.supabase_client import supabase as _service_client

BUCKET = "assistant-files"
SIGNED_URL_TTL = 3600  # seconds
MAX_IMAGE_BYTES = 8 * 1024 * 1024

IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

TEXT_EXTENSIONS = {
    "txt", "md", "csv", "tsv", "json", "xml", "html", "htm",
    "yaml", "yml", "log", "sql", "py", "js", "ts",
}

# Formats the assistant is allowed to generate.
GENERATED_FORMATS = {
    "csv": "text/csv",
    "txt": "text/plain",
    "md": "text/markdown",
    "json": "application/json",
    "html": "text/html",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

_LIST_COLUMNS = "id,name,mime_type,size_bytes,is_generated,conversation_id,created_at"


class FileError(Exception):
    """User-facing file problem. The route turns this into an HTTP error."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _storage():
    if _service_client is None:
        raise FileError("File storage is not configured.", 503)
    return _service_client.storage.from_(BUCKET)


def _safe_name(name: str) -> str:
    cleaned = re.sub(r"[^\w.\-]+", "_", (name or "").strip())
    return cleaned[:120] or "file"


def _ext(name: str) -> str:
    return name.lower().rsplit(".", 1)[-1] if "." in name else ""


def _valid_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        raise FileError("File not found.", 404)


def _check_path(user_id: str, path: str) -> None:
    """A storage path must live inside the caller's own folder."""
    parts = path.split("/")
    if (
        len(parts) < 2
        or parts[0] != user_id
        or any(p in ("", ".", "..") for p in parts)
    ):
        raise FileError("Invalid file path.", 403)


def _max_bytes() -> int:
    return settings.assistant_max_upload_mb * 1024 * 1024


# ---------------------------------------------------------------------------
# Text extraction (libraries are imported lazily so a missing one
# can never stop the whole API from starting)
# ---------------------------------------------------------------------------
def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    limit = settings.assistant_file_text_chars
    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    size = 0
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        pages.append(f"[Page {number}]\n{text}")
        size += len(text)
        if size > limit:
            break
    return "\n\n".join(pages)


def _docx_text(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(parts)


def _xlsx_text(data: bytes) -> str:
    from openpyxl import load_workbook

    limit = settings.assistant_file_text_chars
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    lines: list[str] = []
    size = 0
    try:
        for ws in wb.worksheets:
            lines.append(f"[Sheet: {ws.title}]")
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= 2000 or size > limit:
                    break
                line = " | ".join("" if c is None else str(c) for c in row)
                lines.append(line)
                size += len(line)
            if size > limit:
                break
    finally:
        wb.close()
    return "\n".join(lines)


def extract_text(name: str, mime_type: str | None, data: bytes) -> str | None:
    """Return the file's text, or None if the type is not readable."""
    ext = _ext(name)
    mime = (mime_type or "").lower()
    try:
        if ext == "pdf" or mime == "application/pdf":
            return _pdf_text(data)
        if ext == "docx":
            return _docx_text(data)
        if ext in ("xlsx", "xlsm"):
            return _xlsx_text(data)
        if (
            ext in TEXT_EXTENSIONS
            or mime.startswith("text/")
            or mime in ("application/json", "application/xml")
        ):
            return data.decode("utf-8", errors="replace")
    except Exception:
        return None
    return None


# ---------------------------------------------------------------------------
# Uploaded files
# ---------------------------------------------------------------------------
def register_uploaded_file(
    user_client: Any,
    user_id: str,
    *,
    storage_path: str,
    name: str,
    mime_type: str | None,
    size_bytes: int,
    conversation_id: str | None = None,
) -> dict:
    """Read a file the browser already uploaded, extract its text, save the record."""
    _check_path(user_id, storage_path)

    if size_bytes > _max_bytes():
        raise FileError(
            f"File is too large (max {settings.assistant_max_upload_mb} MB).", 413
        )

    if conversation_id:
        conversation_id = _valid_uuid(conversation_id)
        owned = (
            user_client.table("ai_conversations")
            .select("id")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )
        if not owned.data:
            raise FileError("Conversation not found.", 404)

    try:
        data = _storage().download(storage_path)
    except FileError:
        raise
    except Exception:
        raise FileError("Upload not found in storage. Please upload the file again.", 404)

    if len(data) > _max_bytes():
        raise FileError(
            f"File is too large (max {settings.assistant_max_upload_mb} MB).", 413
        )

    mime = (mime_type or "application/octet-stream").lower()
    text = None
    if mime not in IMAGE_TYPES:  # images are sent to the model as pictures, not text
        text = extract_text(name, mime, data)
        if text:
            text = text[: settings.assistant_file_text_chars]

    result = (
        user_client.table("ai_files")
        .insert(
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "name": name[:255],
                "mime_type": mime,
                "size_bytes": len(data),
                "storage_path": storage_path,
                "extracted_text": text,
                "is_generated": False,
            }
        )
        .execute()
    )
    if not result.data:
        raise FileError("Could not save the file record.", 500)
    return result.data[0]


# ---------------------------------------------------------------------------
# Reading / listing
# ---------------------------------------------------------------------------
def list_files(
    user_client: Any,
    conversation_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    query = user_client.table("ai_files").select(_LIST_COLUMNS)
    if conversation_id:
        query = query.eq("conversation_id", _valid_uuid(conversation_id))
    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data or []


def get_file(user_client: Any, file_id: str) -> dict:
    """Full row (including extracted_text). RLS means only the owner can see it."""
    file_id = _valid_uuid(file_id)
    result = (
        user_client.table("ai_files").select("*").eq("id", file_id).limit(1).execute()
    )
    if not result.data:
        raise FileError("File not found.", 404)
    return result.data[0]


def load_attachments(user_client: Any, file_ids: list[str]) -> list[dict]:
    """Rows for the given ids. Ids that are not the user's own are silently dropped."""
    ids: list[str] = []
    for fid in file_ids[:10]:
        try:
            ids.append(str(uuid.UUID(str(fid))))
        except (ValueError, TypeError):
            continue
    if not ids:
        return []
    result = user_client.table("ai_files").select("*").in_("id", ids).execute()
    return result.data or []


def is_image(row: dict) -> bool:
    return (row.get("mime_type") or "").lower() in IMAGE_TYPES


def image_data_url(user_id: str, row: dict) -> str | None:
    """Base64 data URL so the model can see an uploaded image. None if not an image / too big."""
    if not is_image(row):
        return None
    _check_path(user_id, row["storage_path"])
    try:
        data = _storage().download(row["storage_path"])
    except Exception:
        return None
    if len(data) > MAX_IMAGE_BYTES:
        return None
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{row['mime_type']};base64,{encoded}"


# ---------------------------------------------------------------------------
# Download / delete
# ---------------------------------------------------------------------------
def signed_download_url(user_client: Any, user_id: str, file_id: str) -> dict:
    row = get_file(user_client, file_id)  # ownership enforced by RLS
    _check_path(user_id, row["storage_path"])

    try:
        res = _storage().create_signed_url(
            row["storage_path"], SIGNED_URL_TTL, options={"download": row["name"]}
        )
    except TypeError:
        res = _storage().create_signed_url(row["storage_path"], SIGNED_URL_TTL)

    url = res.get("signedURL") or res.get("signedUrl")
    if not url:
        raise FileError("Could not create a download link.", 500)
    if url.startswith("/"):  # older storage clients return a relative path
        url = f"{settings.supabase_url}/storage/v1{url}"
    return {"url": url, "expires_in": SIGNED_URL_TTL}


def delete_file(user_client: Any, user_id: str, file_id: str) -> None:
    row = get_file(user_client, file_id)
    _check_path(user_id, row["storage_path"])
    try:
        _storage().remove([row["storage_path"]])
    except Exception:
        pass  # the record is removed below either way
    user_client.table("ai_files").delete().eq("id", row["id"]).execute()


# ---------------------------------------------------------------------------
# Files created BY the assistant
# ---------------------------------------------------------------------------
def _cell(value: Any) -> Any:
    """Keep numbers as numbers; stop text from being run as a spreadsheet formula."""
    if value is None:
        return ""
    if isinstance(value, (int, float, bool)):
        return value
    text = str(value)
    return "'" + text if text[:1] in ("=", "@") else text


def _build_csv(rows: list[list[Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow([_cell(v) for v in row])
    return buffer.getvalue().encode("utf-8-sig")  # BOM so Excel reads UTF-8 correctly


def _build_xlsx(rows: list[list[Any]]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append([_cell(v) for v in row])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def create_generated_file(
    user_client: Any,
    user_id: str,
    *,
    filename: str,
    file_format: str,
    text: str | None = None,
    rows: list[list[Any]] | None = None,
    conversation_id: str | None = None,
) -> dict:
    """
    Create a downloadable file for the user.
      - xlsx          needs `rows`  (list of rows, first row = headers)
      - csv           uses `rows` if given, otherwise `text`
      - txt/md/json/html   use `text`
    Returns the saved ai_files row.
    """
    fmt = (file_format or "").lower().lstrip(".")
    if fmt not in GENERATED_FORMATS:
        raise FileError(
            f"Unsupported format '{file_format}'. Use one of: {', '.join(GENERATED_FORMATS)}."
        )

    if fmt == "xlsx":
        if not rows:
            raise FileError("xlsx files need 'rows'.")
        data = _build_xlsx(rows)
    elif fmt == "csv" and rows:
        data = _build_csv(rows)
    else:
        if text is None:
            raise FileError("This file type needs 'text' content.")
        data = text.encode("utf-8")

    if len(data) > _max_bytes():
        raise FileError("Generated file is too large.", 413)

    name = _safe_name(filename)
    if not name.lower().endswith(f".{fmt}"):
        name = f"{name}.{fmt}"
    path = f"{user_id}/generated/{uuid.uuid4().hex}_{name}"
    mime = GENERATED_FORMATS[fmt]

    _storage().upload(
        path,
        data,
        file_options={"content-type": mime, "upsert": "true"},
    )

    preview = None
    if fmt != "xlsx":
        preview = data.decode("utf-8-sig", errors="replace")[
            : settings.assistant_file_text_chars
        ]

    if conversation_id:
        conversation_id = _valid_uuid(conversation_id)

    try:
        result = (
            user_client.table("ai_files")
            .insert(
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "name": name,
                    "mime_type": mime,
                    "size_bytes": len(data),
                    "storage_path": path,
                    "extracted_text": preview,
                    "is_generated": True,
                }
            )
            .execute()
        )
        if not result.data:
            raise FileError("Could not save the generated file.", 500)
    except Exception:
        try:
            _storage().remove([path])
        except Exception:
            pass
        raise

    return result.data[0]