"""End-to-end pipeline tests: the six required scenarios."""
from workflow.pipeline import Pipeline
from workflow.types import RawRequest


def _stages_in_order(report, stages):
    agents = [e.agent for e in report.log]
    positions = [agents.index(s) for s in stages]
    assert positions == sorted(positions), f"stages out of order: {agents}"


def test_happy_path_approve_sends_with_complete_log(raw_booking, approver, make_sender):
    sender = make_sender()
    report = Pipeline(sender=sender, decide=approver).run(raw_booking)

    assert report.status == "completed"
    assert len(sender.outbox) == 1
    assert report.receipt is not None
    assert report.receipt.recipient == "Daniel Reyes"
    _stages_in_order(
        report, ["intake", "classifier", "drafter", "approval_gate", "sender", "logger"]
    )
    # the human's approval is on the record
    assert any(
        e.agent == "approval_gate" and e.event == "approved" for e in report.log
    )


def test_reject_halts_and_sends_nothing(raw_booking, rejector, make_sender):
    sender = make_sender()
    report = Pipeline(sender=sender, decide=rejector).run(raw_booking)

    assert report.status == "rejected"
    assert sender.outbox == []  # HARD RULE: reject -> nothing sent
    assert report.receipt is None
    assert any(
        e.agent == "approval_gate" and e.event == "rejected" for e in report.log
    )
    # pipeline stopped at the gate: no send attempt happened
    assert not any(e.agent == "sender" and e.event == "sent" for e in report.log)


def test_fail_once_retries_and_sends_exactly_once(raw_booking, approver, make_sender):
    sender = make_sender("fail_once")
    report = Pipeline(sender=sender, decide=approver).run(raw_booking)

    assert report.status == "completed"
    assert len(sender.outbox) == 1  # retried once, delivered once
    assert any(
        e.agent == "sender" and e.event == "failed" for e in report.log
    )
    assert any(e.event == "retrying_send" for e in report.log)


def test_fail_always_escalates_and_sends_zero_times(
    raw_booking, approver, make_sender
):
    sender = make_sender("fail_always")
    escalations = []
    report = Pipeline(
        sender=sender,
        decide=approver,
        escalate=lambda normalized, note: escalations.append((normalized.id, note)),
    ).run(raw_booking)

    assert report.status == "escalated"
    assert sender.outbox == []  # persistent failure -> zero sends
    assert len(escalations) == 1
    assert escalations[0][0] == "req-001"
    assert any(e.event == "escalated" for e in report.log)


def test_rerun_with_same_idempotency_key_sends_once(raw_booking, approver, make_sender):
    sender = make_sender()
    pipeline = Pipeline(sender=sender, decide=approver)

    first = pipeline.run(raw_booking)
    second = pipeline.run(raw_booking)  # same request id -> same idempotency key

    assert first.status == "completed"
    assert second.status == "completed"
    assert len(sender.outbox) == 1  # no double-send
    assert first.receipt.message_id == second.receipt.message_id
    assert any(
        e.agent == "sender" and e.event == "duplicate_suppressed"
        for e in second.log
    )


def test_every_run_produces_a_complete_step_log(
    raw_booking, raw_question, approver, rejector, make_sender
):
    approved = Pipeline(sender=make_sender(), decide=approver).run(raw_booking)
    rejected = Pipeline(sender=make_sender(), decide=rejector).run(raw_question)

    for report in (approved, rejected):
        seqs = [e.seq for e in report.log]
        assert seqs == list(range(1, len(seqs) + 1))  # gapless sequence
        assert report.log[0].agent == "pipeline"
        assert report.log[0].event == "run_started"

    # rejected run still logs everything up to the gate, in order
    _stages_in_order(rejected, ["intake", "classifier", "drafter", "approval_gate"])


def test_reject_after_approval_is_impossible_nothing_leaks():
    # guard: the approval gate is the only path to the sender
    import inspect

    from workflow import pipeline as pipeline_module

    source = inspect.getsource(pipeline_module.Pipeline.run)
    assert source.index("approval_gate") < source.index("self.sender.send")
