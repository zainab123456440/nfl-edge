"""
services/assistant_router.py

Chooses which OpenAI model answers ONE chat turn.

  light route -> short chat and simple database / tool questions (cheap, quick)
  heavy route -> uploaded files, big pasted text, file / lineup generation

The choice is made once per turn, before the first OpenAI call. The same model
is then used for every tool round of that turn, because a previous_response_id
chain should not switch models half-way.

All model names and limits come from settings (environment variables), so you
can change models on Vercel without touching code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# Wording that means "build me a file / export / lineup".
_MAKE_RE = re.compile(
    r"\b(csv|tsv|xlsx|excel|spreadsheet|export|download|lineups?|draftkings|"
    r"(?:create|make|generate|build|write)\b.{0,30}\b(?:file|sheet|report|table))\b",
    re.IGNORECASE,
)

# Wording that points back at a file already in the conversation.
_FILE_REF_RE = re.compile(
    r"\b(file|sheet|spreadsheet|csv|pdf|upload(?:ed)?|attached|column|columns|"
    r"row|rows|document)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Route:
    name: str                       # "light" or "heavy"
    model: str
    effort: str | None              # None = do not send a reasoning block
    max_output_tokens: int
    file_chars: int                 # text of each attached file sent to the model
    reason: str                     # why this route was chosen (for logs)
    fallback_model: str | None = None


def _supports_reasoning(model: str) -> bool:
    return model.startswith(("gpt-5", "gpt-6", "o3", "o4"))


def valid_effort(model: str, effort: str | None) -> str | None:
    """
    Make the reasoning effort legal for the model, so a wrong environment
    variable can never cause an OpenAI 400 error.

      gpt-5.1-*        : low / medium / high / xhigh / max  (no none, no minimal)
      gpt-5, gpt-5-mini: minimal / low / medium / high      (no none)
      gpt-5.x          : none / low / medium / high / ...   (no minimal)
    """
    if not effort or not _supports_reasoning(model):
        return None

    effort = effort.strip().lower()

    if model.startswith("gpt-6.1"):
        return "low" if effort in ("none", "minimal") else effort

    if model == "gpt-5" or model.startswith("gpt-5-"):
        return "minimal" if effort == "none" else effort

    if model.startswith("gpt-5."):
        return "none" if effort == "minimal" else effort

    return effort


def choose_route(
    *,
    message: str,
    attachments: list[dict[str, Any]],
    conversation_has_files: bool,
    cfg: Any,
) -> Route:
    """Pick the light or heavy model for this turn."""
    text = message or ""
    heavy_reason: str | None = None

    if attachments:
        heavy_reason = f"{len(attachments)} attached file(s)"
    elif len(text) >= cfg.ai_heavy_message_chars:
        heavy_reason = f"long message ({len(text):,} chars)"
    elif _MAKE_RE.search(text):
        heavy_reason = "file / lineup generation request"
    elif conversation_has_files and _FILE_REF_RE.search(text):
        heavy_reason = "follow-up about an earlier file"

    if heavy_reason:
        return Route(
            name="heavy",
            model=cfg.ai_heavy_model,
            effort=valid_effort(cfg.ai_heavy_model, cfg.ai_heavy_effort),
            max_output_tokens=cfg.ai_heavy_max_output_tokens,
            file_chars=cfg.ai_heavy_file_chars,
            reason=heavy_reason,
            # If the heavy model is not enabled for this API key, answer with
            # the light model instead of failing the whole request.
            fallback_model=cfg.ai_light_model,
        )

    return Route(
        name="light",
        model=cfg.ai_light_model,
        effort=valid_effort(cfg.ai_light_model, cfg.ai_light_effort),
        max_output_tokens=cfg.ai_light_max_output_tokens,
        file_chars=cfg.assistant_file_text_chars,
        reason="short chat / simple tool question",
    )