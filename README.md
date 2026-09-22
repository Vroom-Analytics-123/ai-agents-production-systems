# AI Agents, RAG Pipelines & Workflow Automation

Built by [Vroom Analytics](https://vroomanalytics.com) — a working example of our [S01 automation service](https://vroomanalytics.com/automation-demo/).

This is a working 5-agent pipeline that reads an incoming inquiry, classifies
it, drafts a reply, and — only after a human approves it — sends it, with
idempotent delivery and full logging. No network, no API keys, stdlib +
pytest only. Clone it, run the failure drills, steal the patterns.

## The problem it solves

Multi-step work doesn't die inside tools. It dies in the **gaps between
them**: a request gets classified but nobody drafts the reply; a draft
goes out that a human never saw; a send fails silently on a Friday night
and nobody finds out until Monday. Each step works; the handoffs don't.
This repo wires the boring parts correctly:

```
                        +-----------------+
                        |  HUMAN (you)    |
                        |  approve/reject |
                        +--------+--------+
                                 ^
                                 | decision callback
                                 |
raw request --> [intake] --> [classifier] --> [drafter] --> [approval gate] --> [sender] --> [logger]
  RawRequest    normalize   booking /        compose        approve or        idempotent     structured
                + validate  question /       follow-up      REJECT -> halt    delivery      run log
                                complaint    (no invented   NOTHING sent      1 retry then
                                             facts)                          escalate
```

Typed handoffs throughout: each agent receives a dataclass and returns a
dataclass (`src/workflow/types.py`). No free-form dicts cross agent
boundaries — if a field matters, it is named.

## 5-minute setup

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   ```
2. Install the one dependency:
   ```bash
   .venv/bin/pip install -r requirements.txt
   ```
3. Run the whole thing — all 18 tests, including the failure drills:
   ```bash
   .venv/bin/pytest tests/ -q
   ```
   Expect: `18 passed in 0.03s`.

4. Try the drills yourself — edit `tests/test_pipeline.py` or write a
   three-liner with your own request:
   ```python
   from workflow.pipeline import Pipeline
   from workflow.sender import Sender
   from workflow.types import Decision, RawRequest

   report = Pipeline(
       sender=Sender(fail_mode="fail_once"),  # flaky provider drill
       decide=lambda draft: Decision(True, "human", "looks right"),
   ).run(RawRequest(id="demo-1", channel="email",
                    sender_name="Alex", body="Can I book Thursday?"))
   print(report.status)                      # completed — one retry, sent once
   print(len(report.log), "log entries")     # the full audit trail
   ```

## Running the tests

```bash
pip install -r requirements.txt && pytest
```

18 tests, all offline. They cover the happy path, every category, the
approval gate (approve → send; reject → halt with NOTHING sent), both
failure drills (`fail_once` retries exactly once, `fail_always` escalates
with zero sends), idempotency (retried runs never double-send, and the
suppression is keyed per request), and the log's gapless sequence on
every run.

## The approval-gate pattern (and why it exists)

The machine does the reading, routing, and drafting. A human decides what
goes out under the business's name. The decision arrives via an injected
callback, so the gate works identically in tests, behind a Slack approval
button, or as an email reply.

The hard rule is enforced in code, not in documentation: the pipeline
reaches the sender **only** through an approved decision. Reject at the
gate and the run halts — the outbox stays empty and the log records the
rejection.

## Failure drills — run these before launch

The sender takes a `fail_mode` so you can rehearse the bad days:

| Drill | How | Expected |
|---|---|---|
| Flaky provider | `Sender(fail_mode="fail_once")` | one retry, sent **exactly once** |
| Full outage | `Sender(fail_mode="fail_always")` | escalated to a human, sent **zero** times |
| Duplicate webhook | run the pipeline twice with the same request id | single send; second run returns the original receipt (`duplicate_suppressed`) |
| Hostile reviewer | `decide` returns `approved=False` | halted at gate, outbox empty |
| Garbage in | empty body | `IntakeError` before anything runs |

## Structured logging

Every step appends to the run log — attempts, failures, retries,
approvals, rejections, escalations — with gapless sequence numbers.
The log is the audit trail: when something goes wrong at 2am, this is
what you read. In production, ship these entries to your logging stack;
the shape (`seq`, `agent`, `event`, `detail`) is deliberately boring so
it maps 1:1 onto any structured logger.

## Production seams

Marked `PRODUCTION SEAM` in the source — the only places real systems
plug in:

- `drafter.py`: query the real calendar / knowledge base instead of the
  acknowledgment templates. Never invent availability or answers.
- `sender.py`: deliver via your mail/SMS provider. Keep the idempotency
  registry (back it with your provider's idempotency keys or a small DB).
- `approval.py`: wire `decide` to a Slack button, email reply, or dashboard.
- `pipeline.py`: pass an `escalate` callback that pages the human.

Agent logic stays untouched.

## What not to automate

- **Don't auto-send.** The moment a machine sends unreviewed outbound
  under your name, you don't have an automation — you have a liability
  with a cron schedule.
- **Don't retry forever.** One retry, then a human. Infinite retries turn
  a provider outage into a thundering herd aimed at your own reputation.
- **Don't let the drafter invent facts.** A confident wrong answer costs
  more than a slow right one. Templates acknowledge; systems answer.
- **Don't skip the log.** If a step isn't in the log, it didn't happen —
  and you can't debug what didn't happen.
- **Don't route complaints to the happy path.** The classifier sends
  complaints to a human-owned draft first. An upset customer misrouted
  to a booking template is how reviews are written.

## How this maps to the Vroom offer

This is a **Track B** example: multi-agent production systems for
operators and technical buyers — principal-engineer-grade production
ownership, error handling, and monitoring. The Vroom S01 automation
service builds systems like this for real businesses: typed agent
handoffs, a human approval gate on anything outbound, retry-once-then-
escalate delivery, and an audit log on every run. The same repo also
demonstrates the RAG/drafting boundary (the drafter acknowledges but
never invents answers — that pattern is what Vroom's RAG pipelines
fill with real knowledge).

Watch it run live — the same pipeline as a browser demo with you as the
human approval gate, plus the offer, pricing, and companion article —
on Vroom's automation demo page:

**[Watch the live agent demo, see the offer, and read the companion article](https://vroomanalytics.com/automation-demo/)**

## Monthly peace of mind

Setup is just day one. The **$99/mo care plan** keeps this running —
monitoring, fixes, and monthly optimization, so you never think about it
again. Details and signup on the
**[automation demo page](https://vroomanalytics.com/automation-demo/)**.

## License

MIT — see [LICENSE](LICENSE). Use the pattern, keep the human in the loop.
