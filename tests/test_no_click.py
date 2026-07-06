"""No-click / rich_click imports guard test.

Verifies that the ewc-backend application code does not import ``click``
or ``rich_click`` — the backend must be a standalone service without CLI
dependencies.
"""

import ast
import os
import re
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent.parent / "app"


def _collect_python_files(base: Path) -> list[Path]:
    """Return all .py files under *base*, excluding __pycache__."""
    result = []
    for root, _dirs, files in os.walk(base):
        if "__pycache__" in root:
            continue
        for fname in files:
            if fname.endswith(".py"):
                result.append(Path(root) / fname)
    return sorted(result)


def _check_no_click_imports(filepath: Path) -> list[str]:
    """Return a list of violations (import statements that import click/rich_click)."""
    violations = []
    source = filepath.read_text()
    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return [f"{filepath}: SyntaxError — cannot parse"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "click" or alias.name.startswith("click."):
                    violations.append(f"{filepath}:{node.lineno} — import {alias.name}")
                if alias.name == "rich_click" or alias.name.startswith("rich_click."):
                    violations.append(f"{filepath}:{node.lineno} — import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == "click" or node.module.startswith("click.")):
                violations.append(f"{filepath}:{node.lineno} — from {node.module} import ...")
            if node.module and (node.module == "rich_click" or node.module.startswith("rich_click.")):
                violations.append(f"{filepath}:{node.lineno} — from {node.module} import ...")
    return violations


def test_no_click_imports_in_app():
    """No file under app/ imports click or rich_click (AST-based check)."""
    files = _collect_python_files(APP_DIR)
    assert len(files) > 0, "No Python files found under app/"

    all_violations = []
    for f in files:
        all_violations.extend(_check_no_click_imports(f))

    assert all_violations == [], (
        f"click/rich_click imports found in app code:\n" + "\n".join(all_violations)
    )


def test_no_click_import_statements_in_app():
    """No file under app/ has 'import click' or 'from click' import lines."""
    files = _collect_python_files(APP_DIR)
    # Pattern matches actual import statements, not comments/docstrings
    import_pattern = re.compile(
        r"^\s*(import\s+click|from\s+click\s+import|"
        r"import\s+rich_click|from\s+rich_click\s+import)",
        re.MULTILINE,
    )
    for f in files:
        source = f.read_text()
        match = import_pattern.search(source)
        assert match is None, f"{f} contains click/rich_click import: {match.group()}"


def test_no_click_in_pyproject_dependencies():
    """click must not be a direct dependency in pyproject.toml."""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    lines = content.splitlines()
    in_deps = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("dependencies = ["):
            in_deps = True
        elif in_deps and stripped.startswith("]"):
            in_deps = False
        elif in_deps and stripped.startswith('"'):
            dep_name = stripped.strip('"').split(">=")[0].split("==")[0].split("[")[0].strip()
            assert dep_name not in ("click", "rich_click"), (
                f"click/rich_click found as direct dependency: {stripped}"
            )
