"""pipeline: wire the agents together.

The flow, enforced in code:

    intake -> classifier -> drafter -> APPROVAL GATE -> sender -> log

- The sender is unreachable until the human approves. Reject at the
  gate and the run halts: nothing is sent, and the log says so.
- The sender retries ONCE on failure, then the run escalates to a human
  instead of retrying forever or failing silently.
- Every step appends to the run log, including the logger's own entry.
"""
from __future__ import annotations

from typing import Callable

from . import approval, classifier, drafter, intake
from .approval import DecideFn
from .runlog import RunLog
from .sender import Sender, SendError
from .types import NormalizedRequest, RawRequest, RunReport

EscalateFn = Callable[[NormalizedRequest, str], None]
MAX_SEND_ATTEMPTS = 2  # one try + one retry, then a human takes over


class Pipeline:
    def __init__(
        self,
        sender: Sender,
        decide: DecideFn,
        escalate: EscalateFn | None = None,
    ) -> None:
        self.sender = sender
        self.decide = decide
        self.escalate = escalate

    def run(self, raw: RawRequest) -> RunReport:
        log = RunLog()
        log.record("pipeline", "run_started", raw.id)

        normalized = intake.normalize(raw)
        log.record("intake", "normalized",
                   f"{normalized.channel} from {normalized.sender_name}")

        classification = classifier.classify(normalized)
        log.record("classifier", f"routed:{classification.category}",
                   f"confidence={classification.confidence:.2f}")

        draft = drafter.compose(normalized, classification)
        log.record("drafter", "drafted", draft.subject)

        decision = approval.approval_gate(draft, self.decide, log)
        if not decision.approved:
            log.record("pipeline", "halted",
                       "rejected at approval gate — nothing sent")
            log.record("logger", "run_logged", f"{len(log.entries)} entries")
            return RunReport(run_id=raw.id, status="rejected",
                             log=log.entries, note=decision.reason)

        idempotency_key = f"send-{normalized.id}"
        receipt = None
        attempts = 0
        while attempts < MAX_SEND_ATTEMPTS:
            try:
                receipt = self.sender.send(draft, idempotency_key, log)
                break
            except SendError as exc:
                attempts += 1
                if attempts >= MAX_SEND_ATTEMPTS:
                    note = f"send failed after {attempts} attempts: {exc}"
                    log.record("pipeline", "escalated", note)
                    if self.escalate is not None:
                        self.escalate(normalized, note)
                    log.record("logger", "run_logged", f"{len(log.entries)} entries")
                    return RunReport(run_id=raw.id, status="escalated",
                                     log=log.entries, note=note)
                log.record("pipeline", "retrying_send",
                           f"attempt {attempts + 1} of {MAX_SEND_ATTEMPTS}")

        log.record("pipeline", "run_completed",
                   receipt.message_id if receipt else "")
        log.record("logger", "run_logged", f"{len(log.entries)} entries")
        return RunReport(run_id=raw.id, status="completed",
                         log=log.entries, receipt=receipt)
