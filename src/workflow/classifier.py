"""classifier: route the request to booking / question / complaint.

Deterministic keyword routing. Complaint wins ties on purpose: an upset
customer misrouted to a booking template is worse than a booking
misrouted to a human-reviewed complaint draft — and every draft is
human-reviewed anyway (see approval.py).
"""
from __future__ import annotations

from .types import Classification, NormalizedRequest

_BOOKING = ("book", "booking", "appointment", "schedule", "reserve", "slot",
            "reschedule", "cancel my appointment")
_COMPLAINT = ("complaint", "complain", "refund", "charged twice", "terrible",
              "angry", "disappointed", "broken", "awful", "unacceptable",
              "furious", "worst")


def _hits(body: str, keywords: tuple[str, ...]) -> tuple[str, ...]:
    lowered = body.lower()
    return tuple(k for k in keywords if k in lowered)


def classify(request: NormalizedRequest) -> Classification:
    complaint_hits = _hits(request.body, _COMPLAINT)
    if complaint_hits:
        return Classification(
            request_id=request.id,
            category="complaint",
            confidence=min(0.6 + 0.1 * len(complaint_hits), 0.95),
            matched_keywords=complaint_hits,
        )
    booking_hits = _hits(request.body, _BOOKING)
    if booking_hits:
        return Classification(
            request_id=request.id,
            category="booking",
            confidence=min(0.6 + 0.1 * len(booking_hits), 0.95),
            matched_keywords=booking_hits,
        )
    return Classification(
        request_id=request.id, category="question", confidence=0.5,
        matched_keywords=(),
    )
