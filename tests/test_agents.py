"""Unit tests for the individual agents."""
import pytest

from workflow import approval, classifier, drafter, intake
from workflow.runlog import RunLog
from workflow.sender import Sender
from workflow.types import Decision, Draft, RawRequest


def _norm(**kw):
    defaults = dict(id="req-x", channel="email", sender_name="Alex", body="Hello?")
    defaults.update(kw)
    return intake.normalize(RawRequest(**defaults))


def test_intake_normalizes_whitespace_and_channel():
    n = _norm(channel="  SMS ", sender_name="  Jo  ", body="  need a slot  ")
    assert n.channel == "sms"
    assert n.sender_name == "Jo"
    assert n.body == "need a slot"


def test_intake_rejects_empty_body():
    with pytest.raises(intake.IntakeError):
        _norm(body="   ")


def test_classifier_routes_booking_question_complaint(raw_booking, raw_question, raw_complaint):
    assert classifier.classify(_norm(body=raw_booking.body)).category == "booking"
    assert classifier.classify(_norm(body=raw_question.body)).category == "question"
    assert classifier.classify(_norm(body=raw_complaint.body)).category == "complaint"


def test_classifier_complaint_wins_over_booking_keywords():
    n = _norm(body="I want to book again but I'm angry about being charged twice")
    assert classifier.classify(n).category == "complaint"


def test_drafter_produces_typed_draft_for_each_category():
    for category in ("booking", "question", "complaint"):
        n = _norm()
        draft = drafter.compose(n, classifier.Classification(
            request_id=n.id, category=category, confidence=0.8))
        assert isinstance(draft, Draft)
        assert draft.recipient == "Alex"
        assert draft.request_id == "req-x"
        assert n.sender_name in draft.body
        assert len(draft.subject) > 0


def test_drafter_never_invents_an_answer():
    # the question draft acknowledges and routes — it does not fabricate facts
    n = _norm(body="What are your Saturday hours?")
    c = classifier.classify(n)
    draft = drafter.compose(n, c)
    assert "9" not in draft.body and "1pm" not in draft.body.lower()


def test_approval_gate_returns_human_decision_verbatim():
    draft = Draft(request_id="r", category="question", recipient="A",
                  subject="s", body="b")
    log = RunLog()
    yes = approval.approval_gate(draft, lambda d: Decision(True, "human", "ok"), log)
    assert yes.approved is True
    no = approval.approval_gate(draft, lambda d: Decision(False, "human", "no"), log)
    assert no.approved is False


def test_sender_rejects_unknown_fail_mode():
    with pytest.raises(ValueError):
        Sender(fail_mode="sometimes")
