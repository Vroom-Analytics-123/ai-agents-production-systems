"""intake: normalize the raw request.

Rejects empty bodies loudly. Everything downstream assumes a real,
non-empty, stripped request — that assumption is enforced here, once.
"""
from __future__ import annotations

from .types import NormalizedRequest, RawRequest


class IntakeError(ValueError):
    """The request was unusable. Nothing else runs."""


def normalize(raw: RawRequest) -> NormalizedRequest:
    body = raw.body.strip()
    if not body:
        raise IntakeError("empty request body — nothing to process")
    request_id = raw.id.strip()
    if not request_id:
        raise IntakeError("request is missing an id")
    channel = raw.channel.strip().lower() or "unknown"
    sender_name = raw.sender_name.strip() or "there"
    return NormalizedRequest(
        id=request_id, channel=channel, sender_name=sender_name, body=body
    )
