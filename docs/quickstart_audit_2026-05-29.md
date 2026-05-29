# Fresh-Clone Quickstart Audit

Date: 2026-05-29
Last refreshed: 2026-05-29 after repository was made public

## Goal

Verify that a first-time developer can clone the repository and run the
stale-memory demo without maintainer-only context.

## Environment

- Machine: local macOS development machine
- Repository state: public GitHub repository
- Clone directory: `/tmp/lgmi-public-quickstart-audit-20260529`
- Python path assumption: use `uv run python`; do not assume a system `python`
  executable exists.
- Node/npm: available locally

## Commands Run

Current public HTTPS clone:

```bash
git clone https://github.com/fengjikui/langgraph-memory-inspector.git /tmp/lgmi-public-quickstart-audit-20260529
```

Result: passed without GitHub authentication.

Earlier private-repo attempts required authenticated clone access. That
condition no longer applies while the repository remains public.

Install Python dependencies:

```bash
uv sync
```

Result: passed.

Check demo readiness without requiring Node/npm:

```bash
uv run lgmi doctor --skip-web
```

Result: passed. The doctor created and inspected:

- 18 checkpoint rows
- 41 write rows
- `examples/relocation_policy_agent/data/checkpoints.sqlite`

Run product proof:

```bash
uv run lgmi prove-demo --reset-demo --json
```

Result: passed. The report included:

- `"checkpoint_count": 18`
- `"write_count": 41`
- `"final_selected_city": "Shanghai"`
- `"latest_residence_city": "Hangzhou"`
- `"passed": true`
- a privacy note saying the proof excludes diagnostic evidence payloads,
  message content, prompts, tokens, and raw database rows

## Findings

1. The README quickstart should explicitly mention prerequisites: `uv`, Node.js,
   and npm.
2. The API command is blocking, so the README should say terminal 1 / terminal
   2 instead of relying on the reader to infer it.
3. A simple `curl /api/summary` health check makes it easier to tell whether the
   backend is running before opening the UI.
4. Browser e2e tests need a Playwright browser install in a clean environment:
   `npx playwright install chromium`.
5. Public HTTPS clone now works, so public launch posts can safely link to the
   repository.

## README Updates Made

- Added prerequisites.
- Clarified terminal 1 / terminal 2.
- Added API health check.
- Added `npx playwright install chromium` before `npm run test:e2e`.

## Verdict

Fresh-clone quickstart now passes through the public HTTPS path. A first-time
developer can clone, install with `uv sync`, run `lgmi doctor --skip-web`, and
prove the stale-memory workflow with `lgmi prove-demo --reset-demo --json`
without maintainer-only context.
