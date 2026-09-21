"""sender: deliver the approved draft.

Two hard rules live here:
1. IDEMPOTENCY. Every send carries an idempotency key. A retried or
   re-run pipeline with the same key returns the original receipt and
   delivers nothing twice. The outbox is the source of truth in tests;
   in production it is your mail/SMS provider's idempotency support.
2. INJECTED FAILURE. fail_mode exists so you can drill the failure paths
   before launch: "fail_once" (flaky provider) and "fail_always" (outage).
   The pipeline retries once, then escalates to a human.
"""
from __future__ import annotations

from .runlog import RunLog
from .types import Draft, SendReceipt

_FAIL_MODES = ("none", "fail_once", "fail_always")


class SendError(RuntimeError):
    """The delivery attempt failed. The pipeline decides: retry or escalate."""


class Sender:
    def __init__(self, fail_mode: str = "none") -> None:
        if fail_mode not in _FAIL_MODES:
            raise ValueError(f"unknown fail_mode {fail_mode!r}; want one of {_FAIL_MODES}")
        self.fail_mode = fail_mode
        self.outbox: list[SendReceipt] = []
        self._registry: dict[str, SendReceipt] = {}
        self._flaked = False

    def send(self, draft: Draft, idempotency_key: str, log: RunLog) -> SendReceipt:
        # Rule 1: same key -> same receipt, no second delivery.
        if idempotency_key in self._registry:
            log.record("sender", "duplicate_suppressed", idempotency_key)
            return self._registry[idempotency_key]

        log.record("sender", "attempt",
                   f"{draft.recipient} key={idempotency_key}")
        if self.fail_mode == "fail_always" or (
            self.fail_mode == "fail_once" and not self._flaked
        ):
            self._flaked = True
            log.record("sender", "failed", f"injected {self.fail_mode}")
            raise SendError(f"injected failure ({self.fail_mode})")

        receipt = SendReceipt(
            idempotency_key=idempotency_key,
            message_id=f"msg-{idempotency_key}",
            recipient=draft.recipient,
        )
        self._registry[idempotency_key] = receipt
        self.outbox.append(receipt)
        log.record("sender", "sent", receipt.message_id)
        return receipt
