# AGENTS.md

## Project description
This repository provides the `link-tracer` package.

It is intended to trace links in Obsidian notes back to source files on disk and to expose that data as JSON via CLI or as dictionaries via API.

## Project Structure
```text
project/
├── .python-version, pyproject.toml        # Runtime & packaging config
├── README.md, LICENSE, AGENTS.md          # Project docs
├── src/link_tracer/                        # Source code
│   ├── __init__.py
│   ├── api.py
│   ├── cli.py
│   └── models.py
├── tests/                                  # Pytest suite
│   ├── conftest.py
│   └── test_core.py
└── docs/                                   # MkDocs source
```

## Coding Standards
- Use modern Python syntax for the configured interpreter version.
- Prefer `pathlib` over `os.path`.
- Keep modules cohesive and functions small.
- Add docstrings to public APIs.


## Development Workflows

### UV Environment & Dependencies
- **Lock:** `uv lock`
- **Sync:** `uv sync` (add `--all-extras` for dev/docs).
- **Update:** `uv lock --upgrade`.
- **Management:** `uv add <pkg>` (use `--dev` for dev); `uv remove <pkg>`; `uv pip list`.

### Execution & Lifecycle
- **Run:** `uv run python -m link_tracer` or `uv run link-tracer`.
- **Dist:** `uv build` (wheel/sdist).
- **Publish:** `uv publish` (or GitHub workflow-based trusted publishing).

### Standards & Git
- **Versioning:** SemVer (`MAJOR.MINOR.PATCH`).
- **Commits:** Conventional Commits (`feat:`, `fix:`, `chore:`, etc.).
- **Automation:** Never commit autonomously unless explicitly requested.

## Testing & QA

### Quality Checks
Prefix commands with `uv run`.
- **Format/Lint:** `ruff format src tests`, `ruff check src tests`
- **Types:** `mypy src`
- **Tests:** `pytest`
- **Pre-commit gate:**
  `uv run ruff format src tests && uv run ruff check src tests && uv run mypy src && uv run pytest`

### Test Guidelines
- Use public APIs in tests.
- Keep imports at the top of test files.
- Use `tmp_path` for filesystem tests.
- Add at least one focused test per non-trivial function.

## Tech Stack Defaults
- **Runtime:** Python 3.12+
- **Package management:** `uv`
- **Build backend:** `hatchling`
- **Formatting/Linting:** `ruff`
- **Type checking:** `mypy` (strict for `src/`)
- **Testing:** `pytest`
- **Docs:** `mkdocs` + Material theme

## Docstring Rules
- **Format:** Google Style (`Args:`, `Returns:`, `Raises:`).
- **Markup:** Markdown ONLY; NO reST/Sphinx directives (`:class:`, etc.).
- **Code/Links:** Backticks (single inline, triple block). MkDocs autorefs (`[MyClass][]`).
- **Types:** Rely on Python type hints; do not duplicate in docstrings.
- **Style:** PEP 257 imperative mood ("Return X", not "Returns X").
- **Length:** One-liners for simple/private. Multi-line/sections ONLY for complex/public APIs. Omit redundant `Args:`/`Returns:`.
- **Staleness:** Always update docstrings, inline comments, and class `Supported modes:` when implementing scaffolds. Treat stale "not yet implemented" text as a bug.

## Architecture & Mechanisms
<placeholder>
