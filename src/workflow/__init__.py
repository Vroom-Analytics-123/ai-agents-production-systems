"""multi-agent-workflow: a 5-agent pipeline with a human approval gate.

Example repo for Vroom Analytics — the engineering behind the
"AI systems that run your business" offer.
"""
from .pipeline import MAX_SEND_ATTEMPTS, EscalateFn, Pipeline
from .sender import Sender, SendError
from .runlog import RunLog

__all__ = [
    "Pipeline",
    "Sender",
    "SendError",
    "RunLog",
    "EscalateFn",
    "MAX_SEND_ATTEMPTS",
]
