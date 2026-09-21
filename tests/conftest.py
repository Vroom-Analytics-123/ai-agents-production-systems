"""Shared fixtures. Adds src/ to the import path so tests work without install."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest  # noqa: E402

from workflow.sender import Sender  # noqa: E402
from workflow.types import Decision, RawRequest  # noqa: E402


@pytest.fixture
def raw_booking():
    return RawRequest(
        id="req-001",
        channel="email",
        sender_name="Daniel Reyes",
        body="Hi, I'd like to book a cleaning for Thursday morning please.",
    )


@pytest.fixture
def raw_question():
    return RawRequest(
        id="req-002",
        channel="web-form",
        sender_name="Priya Nair",
        body="What are your hours on Saturdays?",
    )


@pytest.fixture
def raw_complaint():
    return RawRequest(
        id="req-003",
        channel="sms",
        sender_name="Sam Ortiz",
        body="I'm really disappointed — I was charged twice for my last visit. I want a refund.",
    )


@pytest.fixture
def approver():
    return lambda draft: Decision(
        approved=True, decided_by="human", reason="tone and facts look right"
    )


@pytest.fixture
def rejector():
    return lambda draft: Decision(
        approved=False, decided_by="human", reason="too pushy — rewrite"
    )


@pytest.fixture
def make_sender():
    def _make(fail_mode="none"):
        return Sender(fail_mode=fail_mode)

    return _make
