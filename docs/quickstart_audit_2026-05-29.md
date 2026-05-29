# Fresh-Clone Quickstart Audit

Date: 2026-05-29

## Goal

Verify that a first-time developer can clone the repository and run the
stale-memory demo without maintainer-only context.

## Environment

- Machine: local macOS development machine
- Repository state: private GitHub repository
- Clone directory: `/tmp/lgmi-quickstart-audit`
- Python path assumption: use `uv run python`; do not assume a system `python`
  executable exists.
- Node/npm: available locally

## Commands Run

Initial unauthenticated HTTPS clone failed because the repository is currently
private:

```bash
git clone https://github.com/fengjikui/langgraph-memory-inspector.git /tmp/lgmi-quickstart-audit
```

Result:

```text
fatal: could not read Username for 'https://github.com': Device not configured
```

For the private-repo audit, cloning through GitHub CLI succeeded:

```bash
gh repo clone fengjikui/langgraph-memory-inspector /tmp/lgmi-quickstart-audit
```

Install Python dependencies:

```bash
uv sync
```

Result: passed.

Generate demo checkpoint data:

```bash
uv run python examples/relocation_policy_agent/run_demo.py
```

Result: passed. The demo created:

- 18 checkpoint rows
- 41 write rows
- `examples/relocation_policy_agent/data/checkpoints.sqlite`

Start API:

```bash
uv run lgmi inspect examples/relocation_policy_agent/data/checkpoints.sqlite --no-browser --port 8765
```

Result: passed. Uvicorn served `http://127.0.0.1:8765`.

Check API summary:

```bash
curl -s http://127.0.0.1:8765/api/summary
```

Result: passed. Response included:

- `"checkpoint_count":18`
- `"write_count":41`
- `"thread_count":1`

Install and start web UI:

```bash
cd web
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Result: passed. Vite served `http://127.0.0.1:5173/`.

Run product smoke test:

```bash
uv run python scripts/use_case_smoke.py --reset-demo
```

Result: passed.

```text
PASS 检查器证据链已经证明 stale memory 故障路径。
```

## Findings

1. The README quickstart should explicitly mention prerequisites: `uv`, Node.js,
   and npm.
2. The API command is blocking, so the README should say terminal 1 / terminal
   2 instead of relying on the reader to infer it.
3. A simple `curl /api/summary` health check makes it easier to tell whether the
   backend is running before opening the UI.
4. Browser e2e tests need a Playwright browser install in a clean environment:
   `npx playwright install chromium`.
5. During the private-repo phase, unauthenticated HTTPS clone is expected to
   fail. This goes away when the repository is public.

## README Updates Made

- Added prerequisites.
- Clarified terminal 1 / terminal 2.
- Added API health check.
- Added `npx playwright install chromium` before `npm run test:e2e`.

## Verdict

Fresh-clone quickstart passed after using authenticated clone access for the
private repository. The main demo path is viable for a first-time developer once
the repository is public or the user has GitHub access.
