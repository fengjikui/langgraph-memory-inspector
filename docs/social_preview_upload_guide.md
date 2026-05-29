# GitHub Social Preview Upload Guide

This guide keeps the last manual launch gate small and repeatable. It does not
replace the GitHub Settings upload step, because that action requires repository
settings access.

## Asset

Use:

```text
docs/assets/github-social-preview.png
```

Verified on 2026-05-30:

- Format: PNG
- Size: 1280 x 640 pixels
- File size: 375 KB
- Background: solid, non-transparent

Re-run the local asset check before uploading:

```bash
uv run python scripts/validate_social_preview.py
```

GitHub's current docs say repository social preview images should be PNG, JPG,
or GIF, under 1 MB. GitHub recommends at least 640 x 320 pixels, with 1280 x
640 pixels for best display. The same official docs describe the upload as a
repository Settings action: open Settings, find Social preview, click Edit, then
upload an image.

```text
https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview
```

## Upload Steps

1. Open the repository:
   `https://github.com/fengjikui/langgraph-memory-inspector`
2. Open `Settings`.
3. Find `Social preview`.
4. Click `Edit`.
5. Click `Upload an image...`.
6. Select `docs/assets/github-social-preview.png`.
7. Save the preview.

## After Upload

Update issue #23 with the upload date and close it:

```bash
gh issue comment 23 --body "Uploaded docs/assets/github-social-preview.png as the repository social preview."
gh issue close 23 --reason completed
```

Then confirm the remote launch status no longer reports the social preview as a
manual gate:

```bash
uv run python scripts/launch_status.py
```

Then post the prepared LangChain Forum draft:

```text
docs/langchain_forum_launch_post.md
```

## Validation

After upload, share or preview the repository URL in at least one platform that
renders OpenGraph cards, such as Slack, X, LinkedIn, or a local social-card
debugger. GitHub and external platforms may cache cards, so allow propagation
time before treating a stale card as failure.

The committed regression test also checks that the asset remains a 1280 x 640
PNG under 1 MB:

```bash
uv run pytest tests/test_social_preview.py -q
```
