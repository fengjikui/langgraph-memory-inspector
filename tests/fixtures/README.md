# Test Fixtures

Fixtures here are intentionally tiny and safe to review. They should encode a
single checkpoint debugging pattern and point to `docs/fixture_policy.md` for
the intake rules.

Do not place raw production checkpoint stores or raw debug bundles in this
directory. Use synthetic, redacted, or schema-only fixtures only.

Current fixture groups:

- `synthetic/`: hand-written or reduced fixtures that preserve a real bug
  pattern without private values.
