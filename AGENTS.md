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

## Dependencies

### matterify (>=0.3.0)
Extracts YAML frontmatter from Markdown files. Used to read metadata from Obsidian notes.

**Public API:**
- `scan_directory(path: Path) -> AggregatedResult` — Scan directory recursively for `.md`/`.markdown` files and extract frontmatter in parallel
- `FileEntry` — Per-file result: `file_path`, `frontmatter` (dict), `status`, `error`, `stats`, `file_hash`
- `ScanMetadata` — Scan summary: `total_files`, `files_with_frontmatter`, `files_without_frontmatter`, `errors`, `scan_duration_seconds`, etc.
- `AggregatedResult` — Holds `metadata` (ScanMetadata) and `files` (list[FileEntry])

**Default exclusions:** `.git`, `.obsidian`, `__pycache__`, `.venv`, `venv`, `node_modules`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`

### obsilink (>=0.3.1)
Extracts Obsidian-style wikilinks, Markdown links, and plain URLs from text. Used to parse link targets from note content.

**Public API:**
- `extract_links(source: str | TextReadable) -> list[Link]` — Extract links from `str` or text-readable objects (with `.read()`), returns links in encounter order, preserves duplicates
- `Link` — Frozen dataclass: `type` (LinkType), `target` (str), `alias` (str | None), `heading` (str | None), `blockid` (str | None). Convenience properties: `is_url` (bool), `is_file` (bool), `as_path` (Path)
- `LinkType` — Enum: `WIKILINK`, `WIKILINK_EMBED`, `MARKDOWN_LINK`, `MARKDOWN_EMBED`, `PLAIN_URL`
- `__version__` — Exported package version string

**Behavior notes (from docstrings):**
- `extract_links()` supports raw `str` input and text-readable objects whose `.read()` returns `str`
- Links are returned in encounter order, duplicates are preserved, malformed/partial syntax is silently ignored
- Embed targets (`![[...]]` and `![...](...)`) are included by default
- Fragment parsing is normalized: `target` excludes `#heading`/`^blockid`, which are exposed as `heading` and `blockid`
- `extract_links()` raises `TypeError` for unsupported source types or non-`str` `.read()` results
- `Link.as_path` raises `ValueError` when the target is a URL

### structlog (>=25.5.0)
Structured logging library. Used for consistent, machine-readable log output across the CLI and API.

**Public API:**
- `get_logger(*args, **initial_values)` — Get a configured logger; returns a `BoundLogger`
- `configure(processors=None, wrapper_class=None, context_class=None, logger_factory=None, cache_logger_on_first_use=None)` — Set global defaults for all loggers
- `BoundLogger` — Immutable context carrier with `bind(**new_values)`, `unbind(*keys)`, `new(**new_values)` methods
- Logging methods: `debug()`, `info()`, `warning()`, `error()`, `critical()`, `log(level, **kw)`
- `make_filtering_bound_logger(min_level)` — Create a fast, level-filtering logger (supports async variants: `ainfo()`, `adebug()`, etc.)
- `PrintLogger` — Simple logger that prints to stdout/stderr (useful for CLI)

### click (>=8.3.2)
Command-line interface toolkit. Used to build the `link-tracer` CLI.

**Public API:**
- `@command(name=None, cls=None, **attrs)` — Decorator to create a CLI command
- `@group(name=None, cls=None, **attrs)` — Decorator to create a command group (subcommands)
- `@option(*param_decls, cls=None, **attrs)` — Add an option to a command
- `@argument(*param_decls, cls=None, **attrs)` — Add a positional argument to a command
- `@pass_context` — Pass the `Context` object to the callback
- `Context` — Holds runtime state; `obj` attribute for user data, `meta` for extension data
- `echo(message, file=None, nl=True, err=False, color=None)` — Print output (better than `print()`)
- `secho(message, **styles)` — Styled echo (combines `echo()` + `style()`)
- `style(text, fg=None, bg=None, bold=None, dim=None, underline=None, **styles)` — Apply ANSI styling
- `progressbar(iterable=None, length=None, label=None, **kwargs)` — Display a progress bar
- `confirm(text, default=False, abort=False)` — Prompt for yes/no confirmation
- `prompt(text, default=None, hide_input=False, **kwargs)` — Prompt for user input
- `File` — File path parameter type with lazy open/close
- `Path` — Path parameter type with existence/type validation

**Supported formats:**
- Wikilinks: `[[Note]]`, `[[Note|Alias]]`, `[[Page#Heading]]`, `[[Note^block]]`, `[[Page#Heading^block]]`, `![[Embed]]`
- Markdown links: `[Text](url)`, `![Image](path)`
- Plain URLs: `https://`, `http://`, `ftp://`, `file://`, `mailto:`

## Docstring Rules
- **Format:** Google Style (`Args:`, `Returns:`, `Raises:`).
- **Markup:** Markdown ONLY; NO reST/Sphinx directives (`:class:`, etc.).
- **Code/Links:** Backticks (single inline, triple block). MkDocs autorefs (`[MyClass][]`).
- **Types:** Rely on Python type hints; do not duplicate in docstrings.
- **Style:** PEP 257 imperative mood ("Return X", not "Returns X").
- **Length:** One-liners for simple/private. Multi-line/sections ONLY for complex/public APIs. Omit redundant `Args:`/`Returns:`.
- **Staleness:** Always update docstrings, inline comments, and class `Supported modes:` when implementing scaffolds. Treat stale "not yet implemented" text as a bug.

## Architecture & Mechanisms

### Metadata Extraction
`link-tracer` uses `matterify.scan_directory()` to extract YAML frontmatter from Obsidian markdown notes. The `AggregatedResult` provides per-file `frontmatter` dicts (via `FileEntry.frontmatter`) and scan-level statistics (via `ScanMetadata`). This metadata is combined with link-tracing data to produce enriched JSON/dict output.

### Link Extraction
`link-tracer` uses `obsilink.extract_links()` to parse Obsidian wikilinks, Markdown links, and plain URLs from note content. Each `Link` provides structured access to the target, alias, heading, and block ID. The `Link.is_url` property distinguishes external URLs, while `Link.is_file` identifies file-like internal targets and `Link.as_path` converts those internal targets to `Path` objects for filesystem resolution.
