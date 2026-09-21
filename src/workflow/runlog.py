"""The logger agent: an append-only structured run log.

Every pipeline step appends here. The log is the audit trail — in
production this is what you read at 2am when something went wrong.
"""
from __future__ import annotations

from .types import LogEntry


class RunLog:
    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    def record(self, agent: str, event: str, detail: str = "") -> LogEntry:
        entry = LogEntry(seq=len(self.entries) + 1, agent=agent,
                         event=event, detail=detail)
        self.entries.append(entry)
        return entry
