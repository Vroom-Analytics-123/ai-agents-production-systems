"""Edge-case regression tests: three real gaps found during the port.

- intake: the missing-id rejection had no test (only the empty-body path did).
- pipeline: `escalate` is optional — the fail_always path without a callback
  had no test.
- sender: idempotency suppresses retries with the same key — but nothing
  proved two DIFFERENT requests still each deliver once (i.e. suppression
  is key-scoped, not a global "already sent" flag).
"""
import pytest

from workflow import intake
from workflow.pipeline import Pipeline
from workflow.sender import Sender
from workflow.types import RawRequest


def test_intake_rejects_missing_id():
    with pytest.raises(intake.IntakeError):
        intake.normalize(
            RawRequest(id="   ", channel="email",
                       sender_name="Alex", body="Hi there")
        )


def test_fail_always_without_escalate_callback_still_escalates_cleanly(
    raw_booking, approver, make_sender
):
    sender = make_sender("fail_always")
    # no escalate callback passed — the pipeline must not blow up
    report = Pipeline(sender=sender, decide=approver).run(raw_booking)

    assert report.status == "escalated"
    assert report.receipt is None
    assert sender.outbox == []  # zero sends, escalated to the human
    assert any(e.event == "escalated" for e in report.log)


def test_idempotency_is_key_scoped_two_requests_send_twice(
    raw_booking, raw_question, approver, make_sender
):
    sender = make_sender()
    pipeline = Pipeline(sender=sender, decide=approver)

    first = pipeline.run(raw_booking)    # id send-req-001
    second = pipeline.run(raw_question)  # id send-req-002 — different key

    assert first.status == "completed"
    assert second.status == "completed"
    assert len(sender.outbox) == 2  # different keys -> both delivered
    assert first.receipt.message_id != second.receipt.message_id
    assert not any(
        e.event == "duplicate_suppressed" for e in second.log
    )
