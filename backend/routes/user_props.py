from statistics import median

from fastapi import APIRouter, Depends, HTTPException, status

from db import get_db
from dependencies.auth import get_current_user
from schemas.prop import AlertCreate, SavedPropCreate

router = APIRouter(tags=["user-props"])


def _uid(user: dict) -> str:
    """
    Return the authenticated Supabase user ID.

    The ID comes exclusively from get_current_user(), which validates
    the Bearer token through Supabase Auth.

    Never accept user_id from the request body, query parameters, or
    URL for private-data ownership.
    """
    if not isinstance(user, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticated user.",
        )

    user_id = user.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticated user.",
        )

    return str(user_id)


def _model_dump(body):
    """Support both Pydantic v2 and v1."""
    if hasattr(body, "model_dump"):
        return body.model_dump()
    return body.dict()


# ---------------------------------------------------------------------
# Saved props
# ---------------------------------------------------------------------

@router.get("/saved-props")
def list_saved(
    user: dict = Depends(get_current_user),
):
    """
    Return only saved props belonging to the authenticated user.
    """
    uid = _uid(user)
    db = get_db()

    saved_result = (
        db.table("saved_props")
        .select("*, players(name,position,team_id)")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .execute()
    )

    saved = saved_result.data or []

    if not saved:
        return {
            "count": 0,
            "data": [],
        }

    player_ids = {
        s["player_id"]
        for s in saved
        if s.get("player_id") is not None
    }

    game_ids = {
        s["game_id"]
        for s in saved
        if s.get("game_id") is not None
    }

    current = []

    if player_ids and game_ids:
        current = (
            db.table("props_current")
            .select("game_id,player_id,market,line")
            .in_("player_id", list(player_ids))
            .in_("game_id", list(game_ids))
            .execute()
            .data
            or []
        )

    lines: dict[tuple, list] = {}

    for current_prop in current:
        line = current_prop.get("line")

        if line is None:
            continue

        key = (
            current_prop.get("game_id"),
            current_prop.get("player_id"),
            current_prop.get("market"),
        )

        lines.setdefault(key, []).append(line)

    result = []

    for saved_prop in saved:
        # Create a copy so the raw Supabase result isn't mutated.
        item = dict(saved_prop)

        player = item.pop("players", None) or {}

        item["player_name"] = player.get("name")
        item["position"] = player.get("position")

        key = (
            item.get("game_id"),
            item.get("player_id"),
            item.get("market"),
        )

        available_lines = lines.get(key)

        item["current_line"] = (
            median(available_lines)
            if available_lines
            else None
        )

        current_line = item.get("current_line")
        saved_line = item.get("line_at_save")

        if current_line is not None and saved_line is not None:
            try:
                item["movement_since_save"] = round(
                    float(current_line) - float(saved_line),
                    2,
                )
            except (TypeError, ValueError):
                item["movement_since_save"] = None
        else:
            item["movement_since_save"] = None

        result.append(item)

    return {
        "count": len(result),
        "data": result,
    }


@router.post(
    "/saved-props",
    status_code=status.HTTP_201_CREATED,
)
def save_prop(
    body: SavedPropCreate,
    user: dict = Depends(get_current_user),
):
    """
    Save a prop for the authenticated user.

    user_id is always overwritten with the authenticated user's ID.
    A client cannot choose another user's ownership.
    """
    uid = _uid(user)
    db = get_db()

    payload = _model_dump(body)

    # Never trust a user_id supplied by the client.
    payload["user_id"] = uid

    if payload.get("line_at_save") is None:
        rows = (
            db.table("props_current")
            .select("line")
            .eq("game_id", body.game_id)
            .eq("player_id", body.player_id)
            .eq("market", body.market)
            .execute()
            .data
            or []
        )

        lines = [
            row["line"]
            for row in rows
            if row.get("line") is not None
        ]

        payload["line_at_save"] = (
            median(lines)
            if lines
            else None
        )

    try:
        response = (
            db.table("saved_props")
            .upsert(
                payload,
                on_conflict="user_id,player_id,game_id,market",
            )
            .execute()
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not save prop. Please try again.",
        )

    if response.data:
        return response.data[0]

    return payload


@router.delete(
    "/saved-props/{saved_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unsave_prop(
    saved_id: int,
    user: dict = Depends(get_current_user),
):
    """
    Delete a saved prop only if it belongs to the authenticated user.
    """
    uid = _uid(user)

    (
        get_db()
        .table("saved_props")
        .delete()
        .eq("id", saved_id)
        .eq("user_id", uid)
        .execute()
    )

    return None


# ---------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------

@router.get("/alerts")
def list_alerts(
    user: dict = Depends(get_current_user),
):
    """
    Return only alerts belonging to the authenticated user.
    """
    uid = _uid(user)

    rows = (
        get_db()
        .table("alerts")
        .select("*, players(name)")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )

    result = []

    for row in rows:
        item = dict(row)

        player = item.pop("players", None) or {}
        item["player_name"] = player.get("name")

        result.append(item)

    return {
        "count": len(result),
        "data": result,
    }


@router.post(
    "/alerts",
    status_code=status.HTTP_201_CREATED,
)
def create_alert(
    body: AlertCreate,
    user: dict = Depends(get_current_user),
):
    """
    Create an alert owned by the authenticated user.
    """
    uid = _uid(user)

    if (
        body.condition in ("odds_above", "odds_below")
        and body.target_value is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="target_value is required for odds alerts.",
        )

    payload = _model_dump(body)

    # Ownership always comes from the authenticated token.
    payload["user_id"] = uid

    try:
        response = (
            get_db()
            .table("alerts")
            .insert(payload)
            .execute()
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create alert. Please try again.",
        )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create alert. Please try again.",
        )

    return response.data[0]


@router.patch("/alerts/{alert_id}/toggle")
def toggle_alert(
    alert_id: int,
    user: dict = Depends(get_current_user),
):
    """
    Toggle an alert only when it belongs to the authenticated user.
    """
    uid = _uid(user)
    db = get_db()

    response = (
        db.table("alerts")
        .select("is_active")
        .eq("id", alert_id)
        .eq("user_id", uid)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )

    current_state = bool(
        response.data[0].get("is_active", False)
    )
    new_state = not current_state

    (
        db.table("alerts")
        .update({"is_active": new_state})
        .eq("id", alert_id)
        .eq("user_id", uid)
        .execute()
    )

    return {
        "id": alert_id,
        "is_active": new_state,
    }


@router.delete(
    "/alerts/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_alert(
    alert_id: int,
    user: dict = Depends(get_current_user),
):
    """
    Delete an alert only if it belongs to the authenticated user.
    """
    uid = _uid(user)

    (
        get_db()
        .table("alerts")
        .delete()
        .eq("id", alert_id)
        .eq("user_id", uid)
        .execute()
    )

    return None