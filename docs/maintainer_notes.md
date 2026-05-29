# Maintainer Notes

## 2026-05-29

### Diagnostic Cards Become Debug Navigation

User value improved:

- Before: diagnostics were informative cards, but they did not help the user
  move through the debugging workflow.
- After: diagnostics now include checkpoint, state path, and write channel
  evidence. Clicking a diagnostic selects the related checkpoint.

Why it matters:

- A real developer does not want to read every checkpoint manually. They want to
  jump from "this looks wrong" to "show me the first state snapshot that proves
  it." This change moves the product from a JSON viewer toward an actual
  debugging tool.

Verified:

- `uv run pytest -q`
- `cd web && npm run build`
- Rendered local UI screenshot with live FastAPI data and confirmed the
  diagnostics panel is visible in the first viewport.

Next:

- Highlight the diagnostic-linked write channel inside the Writes tab.
- Add a proper browser interaction test once the frontend test stack is added.
