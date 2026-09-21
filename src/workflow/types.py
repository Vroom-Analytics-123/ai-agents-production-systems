"""Typed handoffs between agents.

Every agent receives a dataclass and returns a dataclass. No free-form
dicts cross agent boundaries — if a field matters, it is named here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Category = Literal["booking", "question", "complaint"]
RunStatus = Literal["completed", "rejected", "escalated"]


@dataclass(frozen=True)
class RawRequest:
    """Untrusted input as it arrives from a channel."""

    id: str
    channel: str  # e.g. "email", "sms", "web-form"
    sender_name: str
    body: str


@dataclass(frozen=True)
class NormalizedRequest:
    """Cleaned request. Empty bodies are rejected by intake, never here."""

    id: str
    channel: str
    sender_name: str
    body: str


@dataclass(frozen=True)
class Classification:
    request_id: str
    category: Category
    confidence: float
    matched_keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class Draft:
    """Outbound message composed but NOT sent. Sending requires a human."""

    request_id: str
    category: Category
    recipient: str
    subject: str
    body: str


@dataclass(frozen=True)
class Decision:
    """The human's verdict at the approval gate."""

    approved: bool
    decided_by: str = "human"
    reason: str = ""


@dataclass(frozen=True)
class SendReceipt:
    idempotency_key: str
    message_id: str
    recipient: str


@dataclass
class LogEntry:
    seq: int
    agent: str
    event: str
    detail: str = ""


@dataclass
class RunReport:
    run_id: str
    status: RunStatus
    log: list[LogEntry] = field(default_factory=list)
    receipt: SendReceipt | None = None
    note: str = ""
