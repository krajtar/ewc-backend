"""Guard test: ensure no click/rich_click imports in the app package."""

import pathlib
import re

import pytest

APP_DIR = pathlib.Path(__file__).resolve().parent.parent / "app"

FORBIDDEN_PATTERNS = [
    re.compile(r"^\s*import\s+click\b", re.MULTILINE),
    re.compile(r"^\s*from\s+click\b", re.MULTILINE),
    re.compile(r"^\s*import\s+rich_click\b", re.MULTILINE),
    re.compile(r"^\s*from\s+rich_click\b", re.MULTILINE),
]


def _find_python_files() -> list[pathlib.Path]:
    return list(APP_DIR.rglob("*.py"))


@pytest.mark.parametrize("filepath", _find_python_files())
def test_no_click_imports(filepath: pathlib.Path) -> None:
    """No Python file under app/ may import click or rich_click."""
    content = filepath.read_text()
    for pattern in FORBIDDEN_PATTERNS:
        matches = pattern.findall(content)
        assert not matches, (
            f"{filepath} contains forbidden import matching {pattern.pattern}"
        )
