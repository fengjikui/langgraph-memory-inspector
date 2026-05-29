from __future__ import annotations

from pathlib import Path

from scripts.validate_social_preview import validate_social_preview


def test_github_social_preview_asset_matches_github_recommendations() -> None:
    result = validate_social_preview(Path("docs/assets/github-social-preview.png"))

    assert result["format"] == "PNG"
    assert result["width"] == 1280
    assert result["height"] == 640
    assert result["size_bytes"] < result["max_bytes"]
