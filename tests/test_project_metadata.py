from __future__ import annotations

import tomllib
from pathlib import Path


def test_project_metadata_points_users_to_support_channels() -> None:
    metadata = tomllib.loads(Path("pyproject.toml").read_text())
    project = metadata["project"]

    assert "langgraph" in project["keywords"]
    assert "checkpoint-debugging" in project["keywords"]
    assert project["urls"]["Repository"].endswith("/langgraph-memory-inspector")
    assert project["urls"]["Issues"].endswith("/langgraph-memory-inspector/issues")


def test_project_metadata_advertises_developer_tooling_context() -> None:
    classifiers = set(tomllib.loads(Path("pyproject.toml").read_text())["project"]["classifiers"])

    assert "Intended Audience :: Developers" in classifiers
    assert "Topic :: Software Development :: Debuggers" in classifiers
