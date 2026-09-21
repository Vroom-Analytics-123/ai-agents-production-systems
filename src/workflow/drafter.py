"""drafter: compose the follow-up message.

Deliberate boundary: drafts ACKNOWLEDGE and propose a next step. They
never invent facts (hours, prices, availability) — those come from your
systems at the PRODUCTION SEAM below, or from the human at the gate.
A draft that guesses is a liability, not an automation.
"""
from __future__ import annotations

from .types import Classification, Draft, NormalizedRequest


def compose(request: NormalizedRequest, classification: Classification) -> Draft:
    name = request.sender_name
    category = classification.category

    if category == "booking":
        subject = "Re: your booking request"
        body = (
            f"Hi {name},\n\n"
            "Thanks for reaching out — we'd be glad to find you a time.\n\n"
            f'You wrote: "{request.body}"\n\n'
            # PRODUCTION SEAM: query the real calendar/booking system here
            # and offer concrete slots. Never invent availability.
            "I've flagged your preferred timing for our team and we'll "
            "confirm a slot shortly.\n\n"
            "Best regards"
        )
    elif category == "complaint":
        subject = "We're looking into this for you"
        body = (
            f"Hi {name},\n\n"
            "I'm sorry about this — thank you for telling us directly.\n\n"
            f'You wrote: "{request.body}"\n\n'
            "I've escalated this to a person on our team who will follow up "
            "with you personally.\n\n"
            "Best regards"
        )
    else:  # question
        subject = "Re: your question"
        body = (
            f"Hi {name},\n\n"
            "Thanks for the question — it's a good one.\n\n"
            f'You wrote: "{request.body}"\n\n'
            # PRODUCTION SEAM: answer from the approved FAQ / knowledge base
            # here (see the RAG example repo). Never answer from memory.
            "We're pulling the exact answer from our documentation and will "
            "reply shortly.\n\n"
            "Best regards"
        )
    return Draft(
        request_id=request.id,
        category=category,
        recipient=name,
        subject=subject,
        body=body,
    )
