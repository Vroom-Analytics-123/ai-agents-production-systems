"""approval_gate: the human decision point.

This is the highest-leverage thirty seconds in the pipeline. The machine
does the reading, routing, and drafting; a human decides what goes out
under the business's name. The decision callback is injected so the gate
works the same in tests, in a Slack approval button, or in an email reply.

HARD RULE, enforced by the pipeline: a rejected draft halts the run and
NOTHING is sent. There is no code path from the gate to the sender that
bypasses the decision.
"""
from __future__ import annotations

from typing import Callable

from .runlog import RunLog
from .types import Decision, Draft

DecideFn = Callable[[Draft], Decision]


def approval_gate(draft: Draft, decide: DecideFn, log: RunLog) -> Decision:
    log.record("approval_gate", "awaiting_human",
               f"draft for {draft.recipient} ({draft.category})")
    decision = decide(draft)
    log.record(
        "approval_gate",
        "approved" if decision.approved else "rejected",
        decision.reason,
    )
    return decision
