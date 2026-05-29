# Feedback Intake Playbook

Use this when a real LangGraph user reports a checkpoint, memory, retrieval, or
resume bug. The goal is to turn useful feedback into a safe fixture, diagnostic,
test, or documentation fix without asking anyone to upload raw production
checkpoint data.

## First Triage Command

For a GitHub issue:

```bash
uv run python scripts/feedback_intake.py <issue-number>
```

The report classifies likely pattern families, checkpoint backend signals, safe
evidence signals, and obvious privacy-risk phrases. It also prints a maintainer
checklist that keeps the next reply concrete.

The classifier is intentionally simple. Treat it as a guardrail, not a final
decision.

## Evidence Ladder

Ask for the least sensitive evidence that can reproduce or explain the bug:

1. `doctor --issue` report for quickstart, startup, adapter, or store-shape
   problems.
2. Redacted debug bundle for a local SQLite checkpoint copy, followed by
   `audit-debug-bundle`.
3. Small synthetic fixture that reproduces the state shape.
4. Schema-only snapshot for backend compatibility or migration issues.
5. Private maintainer review only if the user explicitly opts in and public
   redaction is not enough.

Do not request raw production checkpoint stores, prompts, tokens, credentials,
or unredacted user state in public issues.

## Classification Buckets

Use the first matching bucket that would change the product:

- New diagnostic: the report describes a recurring state pattern the inspector
  should detect deterministically.
- Existing diagnostic fixture: the report validates or tunes a diagnostic that
  already appears in `docs/diagnostic_matrix.md`.
- Adapter issue: the backend shape, version, namespace, or migration behavior
  prevents safe inspection.
- UX friction: the tool can already inspect the bug, but the user cannot find
  the right command, checkpoint, filter, or export path.
- Documentation gap: the workflow exists, but the public materials did not make
  the safe path obvious.

## Acceptance Criteria For Follow-Up Issues

Every follow-up diagnostic or fixture issue should include:

- one user-visible failure sentence
- backend shape and checkpoint namespace assumptions
- state path or write channel that should be highlighted
- safest available evidence type: redacted, synthetic, or schema-only
- one command that proves the fix
- whether `docs/diagnostic_matrix.md` needs a new or updated row

## Close The Loop

When a useful report becomes a code or fixture change:

1. Link the follow-up issue or commit in the original feedback thread.
2. Update `docs/diagnostic_matrix.md` if a diagnostic or fixture changed.
3. Add or update a regression test before closing the follow-up.
4. Thank the reporter for the bug pattern, not only for trying the demo.

This is the product loop: real debugging pain becomes safe evidence, safe
evidence becomes a fixture, and the fixture becomes a diagnostic users can
trust.
