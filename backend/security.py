"""Cron routes must send:  Authorization: Bearer <CRON_SECRET>"""
import secrets

from fastapi import Header, HTTPException

from config import CRON_SECRET


def verify_cron(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {CRON_SECRET}" if CRON_SECRET else None
    if not expected or not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")