"""Simple Supabase Storage helpers for uploaded lineup files."""

from config.supabase_client import supabase

BUCKET = "lineup-files"


def upload_lineup_file(path: str, content: bytes) -> str:
    """
    Upload a file to Supabase Storage and return its storage path.
    """
    supabase.storage.from_(BUCKET).upload(
        path,
        content,
        file_options={
            "content-type": "text/csv",
            "upsert": "true",
        },
    )

    return path


def download_lineup_file(path: str) -> bytes:
    """
    Download a file from Supabase Storage.
    """
    return supabase.storage.from_(BUCKET).download(path)