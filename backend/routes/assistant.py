


from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse

from config.settings import settings
from config.supabase_client import get_user_client
from dependencies.auth import get_current_user

from schemas.assistant import (
    ChatRequest,
    ConversationDetail,
    ConversationOut,
    DownloadUrlOut,
    FileOut,
    MessageOut,
    RegisterFileRequest,
    RenameConversationRequest,
)

from services import assistant_agent as agent
from services import assistant_files as files


router = APIRouter(
    prefix="/assistant",
    tags=["assistant"],
)

log = logging.getLogger("assistant.routes")

MAX_ATTACHMENTS = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(user: dict = Depends(get_current_user)):
    """
    Return the authenticated user and a Supabase client acting as that user.

    This client is intentionally user-scoped and therefore remains protected
    by Supabase RLS for normal user-facing reads/writes.
    """
    access_token = (
        user.get("_access_token")
        or user.get("access_token")
        or ""
    )

    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication token is missing.",
        )

    try:
        db = get_user_client(access_token)

    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="The assistant is not configured.",
        )

    return user, db


def _user_id(user: dict) -> str:
    """
    Get the authenticated user's Supabase UUID.
    """
    value = (
        user.get("user_id")
        or user.get("id")
        or user.get("sub")
        or ""
    )

    if not value:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user id is missing.",
        )

    return str(value)


def _uuid_or_404(value: str) -> str:
    """
    Validate UUID route parameters.
    """
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=404,
            detail="Not found.",
        )


def _sse(event: dict) -> str:
    """
    Convert an event dictionary into an SSE message.
    """
    return (
        f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
    )


def _file_http_error(exc: files.FileError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.message,
    )


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@router.post("/chat")
def chat(
    body: ChatRequest,
    ctx=Depends(_ctx),
):
    """
    Start or continue an AI conversation.

    Important:
    - Authentication uses get_current_user().
    - Normal user-owned reads use the user-scoped Supabase client.
    - ai_messages persistence is handled by assistant_agent.save_message(),
      which uses the server-side service-role client.
    """
    user, db = ctx
    user_id = _user_id(user)

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="The AI service is not configured.",
        )

    # ---------------------------------------------------------------
    # Never-fail message + file_ids handling
    # ---------------------------------------------------------------
    message = (body.message or "").strip()

    file_ids = [
        str(fid)
        for fid in (body.file_ids or [])
        if fid
    ]

    # Only reject when BOTH are empty
    if not message and not file_ids:
        raise HTTPException(
            status_code=400,
            detail="Please enter a message or attach a file.",
        )

    # Always have a usable message when files are present
    if not message and file_ids:
        message = "Please analyze the uploaded file(s)."

    if len(file_ids) > MAX_ATTACHMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Attach at most {MAX_ATTACHMENTS} files.",
        )

    try:
        # ---------------------------------------------------------------
        # Conversation
        # ---------------------------------------------------------------

        if body.conversation_id:
            conversation_id = _uuid_or_404(
                body.conversation_id
            )

            conversation = agent.get_conversation(
                user_client=db,
                user_id=user_id,
                conversation_id=conversation_id,
            )

        else:
            conversation = agent.create_conversation(
                user_client=db,
                user_id=user_id,
                title=message or "New conversation",
            )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

        conversation_id = str(
            conversation.get("id") or ""
        )

        if not conversation_id:
            raise RuntimeError(
                "Conversation id is missing."
            )

        # ---------------------------------------------------------------
        # Validate uploaded files belong to the authenticated user
        # ---------------------------------------------------------------

        if file_ids:
            found = {
                str(item["id"]): item
                for item in files.load_attachments(
                    db,
                    file_ids,
                )
            }

            missing_ids = [
                fid
                for fid in file_ids
                if fid not in found
            ]

            if missing_ids:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "One or more attached files "
                        "could not be found."
                    ),
                )

        # ---------------------------------------------------------------
        # Do NOT save the user message here.
        #
        # run_chat() saves it exactly once.
        #
        # This avoids duplicate user messages.
        # ---------------------------------------------------------------

    except HTTPException:
        raise

    except Exception:
        log.exception(
            "could not start chat"
        )

        raise HTTPException(
            status_code=500,
            detail="Could not start the conversation.",
        )

    # -------------------------------------------------------------------
    # SSE event stream
    # -------------------------------------------------------------------

    def event_stream():
        yield _sse(
            {
                "type": "conversation",
                "conversation_id": conversation_id,
                "title": conversation.get(
                    "title",
                    "New conversation",
                ),
            }
        )

        try:
            for event in agent.run_chat(
                user=user,
                user_client=db,
                conversation_id=conversation_id,
                message=message,
                file_ids=file_ids,
            ):
                yield _sse(event)

        except Exception as exc:
            log.exception(
                "assistant stream failed"
            )

            yield _sse(
                {
                    "type": "error",
                    "message": (
                        str(exc)
                        or "The assistant encountered an unexpected error."
                    ),
                }
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


@router.post(
    "/files",
    response_model=FileOut,
)
def register_file(
    body: RegisterFileRequest,
    ctx=Depends(_ctx),
):
    user, db = ctx
    user_id = _user_id(user)

    try:
        return files.register_uploaded_file(
            db,
            user_id,
            storage_path=body.storage_path,
            name=body.name,
            mime_type=body.mime_type,
            size_bytes=body.size_bytes,
            conversation_id=body.conversation_id,
        )

    except files.FileError as exc:
        raise _file_http_error(exc)


@router.get(
    "/files",
    response_model=list[FileOut],
)
def list_files(
    conversation_id: str | None = None,
    ctx=Depends(_ctx),
):
    _, db = ctx

    try:
        return files.list_files(
            db,
            conversation_id=conversation_id,
        )

    except files.FileError as exc:
        raise _file_http_error(exc)


@router.get(
    "/files/{file_id}/download",
    response_model=DownloadUrlOut,
)
def download_file(
    file_id: str,
    ctx=Depends(_ctx),
):
    user, db = ctx
    user_id = _user_id(user)

    try:
        return files.signed_download_url(
            db,
            user_id,
            file_id,
        )

    except files.FileError as exc:
        raise _file_http_error(exc)


@router.delete(
    "/files/{file_id}",
    status_code=204,
)
def delete_file(
    file_id: str,
    ctx=Depends(_ctx),
):
    user, db = ctx
    user_id = _user_id(user)

    try:
        files.delete_file(
            db,
            user_id,
            file_id,
        )

    except files.FileError as exc:
        raise _file_http_error(exc)

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


@router.get(
    "/conversations",
    response_model=list[ConversationOut],
)
def list_conversations(
    ctx=Depends(_ctx),
):
    user, db = ctx
    user_id = _user_id(user)

    result = (
        db.table("ai_conversations")
        .select(
            "id,title,created_at,updated_at"
        )
        .eq(
            "user_id",
            user_id,
        )
        .order(
            "updated_at",
            desc=True,
        )
        .limit(50)
        .execute()
    )

    return result.data or []


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
def get_conversation(
    conversation_id: str,
    ctx=Depends(_ctx),
):
    user, db = ctx
    user_id = _user_id(user)

    conversation_uuid = _uuid_or_404(
        conversation_id
    )

    try:
        conversation = agent.get_conversation(
            user_client=db,
            user_id=user_id,
            conversation_id=conversation_uuid,
        )

    except RuntimeError:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    result = (
        db.table("ai_messages")
        .select(
            "id,role,content,file_ids,created_at"
        )
        .eq(
            "conversation_id",
            conversation["id"],
        )
        .eq(
            "user_id",
            user_id,
        )
        .in_(
            "role",
            ["user", "assistant"],
        )
        .order(
            "created_at",
        )
        .limit(200)
        .execute()
    )

    messages = [
        MessageOut(
            **{
                **m,
                "file_ids": m.get("file_ids") or [],
            }
        )
        for m in (result.data or [])
        if (
            (m.get("content") or "").strip()
            or m.get("file_ids")
        )
    ]

    return ConversationDetail(
        conversation=ConversationOut(
            **conversation
        ),
        messages=messages,
    )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationOut,
)
def rename_conversation(
    conversation_id: str,
    body: RenameConversationRequest,
    ctx=Depends(_ctx),
):
    user, db = ctx
    user_id = _user_id(user)

    conversation_uuid = _uuid_or_404(
        conversation_id
    )

    title = (body.title or "").strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Conversation title cannot be empty.",
        )

    result = (
        db.table("ai_conversations")
        .update(
            {
                "title": title[:200],
            }
        )
        .eq(
            "id",
            conversation_uuid,
        )
        .eq(
            "user_id",
            user_id,
        )
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return result.data[0]


@router.delete(
    "/conversations/{conversation_id}",
    status_code=204,
)
def delete_conversation(
    conversation_id: str,
    ctx=Depends(_ctx),
):
    user, db = ctx
    user_id = _user_id(user)

    conversation_uuid = _uuid_or_404(
        conversation_id
    )

    result = (
        db.table("ai_conversations")
        .delete()
        .eq(
            "id",
            conversation_uuid,
        )
        .eq(
            "user_id",
            user_id,
        )
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return Response(status_code=204)