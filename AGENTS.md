# AGENTS.md

## Project description

A command-line and Python library tool that scans an Obsidian vault, resolves all wikilinks and Markdown links to real files, and builds a structured representation of the vault’s notes and their relationships. It provides JSON and Python dataclass outputs for a raw vault index, per-note link graphs (with configurable depth, forward links, and backlinks), and a complete vault-wide graph.

## Project Structure
```text
project/
├── .python-version, pyproject.toml        # Runtime & packaging config
├── README.md, LICENSE, AGENTS.md          # Project docs
├── src/vault_net/                        # Source code
│   ├── __init__.py                        # Public surface: exports VaultGraph, VaultIndex, build_note_graph, build_vault_graph, scan_vault
│   ├── __main__.py                        # Module runner: python -m vault_net
│   ├── cli.py                             # Click CLI: note-graph, vault-graph subcommands
│   ├── consts.py                          # Shared constants (_FILE_LINKS_KEY, _POSSIBLE_EXTENSIONS)
│   ├── logging.py                         # structlog + rich console configuration
│   ├── models.py                          # Frozen dataclasses: VaultIndex, VaultGraph, VaultLayered, LinkEdge, etc.
│   ├── note_graph.py                      # build_note_graph(): BFS-scoped subgraph for a single note
│   ├── scan.py                            # scan_vault(): matterify integration, VaultIndex builder
│   ├── transforms.py                      # to_layered(): edge graph → BFS depth-layer list
│   ├── utils.py                           # Link extraction helpers (_extract_file_links, _normalize_lookup_key, _path_for_response)
│   └── vault_graph.py                     # build_vault_graph(): full vault link resolution
├── tests/                                  # Pytest suite
│   ├── __init__.py
│   ├── conftest.py                        # Autouse fixtures: env isolation, structlog suppression
│   ├── fixtures.py                        # Sample vaults, fake matterify dataclasses
│   ├── test_cli.py                        # CLI end-to-end tests (note-graph, vault-graph)
│   ├── test_integration.py                # obsilink integration smoke test
│   ├── test_note_graph.py                 # build_note_graph unit tests (depth, backlinks, circular)
│   ├── test_scan.py                       # scan_vault delegation test
│   ├── test_transforms.py                 # to_layered BFS transform tests
│   └── test_vault_graph.py                # build_vault_graph resolution tests
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
- **Run:** `uv run python -m vault_net` or `uv run vault-net`.
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

### matterify (>=0.4.0)
Extracts YAML frontmatter from Markdown files. Used to read metadata from Obsidian notes and invoke a callback for custom data extraction (link parsing).

**Public API:**
- `scan_directory(path: Path, ..., callback=...) -> ScanResults` — Scan directory recursively for `.md`/`.markdown` files; supports `compute_hash`, `compute_stats`, `compute_frontmatter`, `callback` for custom per-file data, and `exclude` for directory filtering
- `FileEntry` — Per-file result: `file_path`, `frontmatter` (dict), `status`, `error`, `stats` (FileStats), `file_hash`, `custom_data` (callback output)
- `ScanMetadata` — Scan summary: `root`, `total_files`, `files_with_frontmatter`, `files_without_frontmatter`, `errors`, `scan_duration_seconds`, `avg_duration_per_file_ms`, `throughput_files_per_second`
- `ScanResults` — Holds `metadata` (ScanMetadata) and `files` (list[FileEntry])
- `BLACKLIST` (from `matterify.constants`) — Default exclusion tuple

**Default exclusions (BLACKLIST):** `.git`, `.obsidian`, `__pycache__`, `.venv`, `venv`, `node_modules`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`

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


## Command line interface

**Subcommand `note-graph`:** Trace links for a single note.
- `NOTE` (positional): Path to the note file (must exist)
- `--vault-root`: Vault root directory (overrides `VAULT_ROOT` env var)
- `-d/--depth` (int, default=1): Traversal depth (0=source only, 1=direct links, 2+=recursive)
- `-o/--output`: Write JSON output to file instead of stdout
- `--format` (choice: `edges`|`layered`, default=`edges`): Graph representation
- `-e/--exclude-dir` (repeatable): Additional directory names to exclude from traversal
- `--no-default-excludes`: Disable built-in default exclusions
- `--debug`: Enable debug-level structured logging to stderr
- `--verbose`: Enable verbose console output via rich

**Subcommand `vault-graph`:** Trace links for every note in the vault.
- `--vault-root`: Vault root directory (overrides `VAULT_ROOT` env var)
- `-o/--output`: Write JSON output to file instead of stdout
- `-e/--exclude-dir` (repeatable): Additional directory names to exclude
- `--no-default-excludes`: Disable built-in default exclusions
- `--debug`, `--verbose`: Same as `note-graph`

**Vault root resolution:** CLI `--vault-root` > `VAULT_ROOT` env var. Raises `UsageError` if neither is set or path doesn't exist.

**Helper functions:**
- `resolve_vault_root(cli_value: Path | None) -> Path` — Resolve vault root with precedence above
- `emit_json_output(payload: str, output: Path | None) -> None` — Write to stdout or file

**Output:** JSON is always pretty-printed with 2-space indentation.

**Supported link formats:**
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

### Pipeline Overview
The processing pipeline is: **scan → vault graph → note graph → transform → output**.
1. `scan_vault()` scans the vault directory via matterify with a callback that pre-extracts file links per note, returning a `VaultIndex`.
2. `build_vault_graph()` resolves all extracted links across the entire vault into `LinkEdge` objects (resolved/unresolved), returning a `VaultGraph`.
3. `build_note_graph()` scopes the vault graph to a BFS neighborhood around a single note (configurable depth), including both forward links and backlinks.
4. `to_layered()` optionally reshapes the edge graph into a flat BFS depth-layer list (`VaultLayered`).
5. CLI serializes the result as JSON.

### Scanning (`scan.py`)
`scan_vault()` calls `matterify.scan_directory()` with `compute_hash=True`, `compute_stats=True`, `compute_frontmatter=True`, and a `callback` that extracts file links via `obsilink`. The `ScanResults` are converted to a `VaultIndex` with `VaultFile` entries (each carrying pre-extracted `VaultLink` lists). Supports configurable directory exclusions via `extra_exclude_dir` and `no_default_excludes`.

### Vault Graph (`vault_graph.py`)
`build_vault_graph()` builds lookup maps (`name_to_file`, `stem_to_file`, `relative_path_to_file`) from the vault index, then resolves all extracted links to `LinkEdge` objects. Link resolution tries: relative path → direct name → name + extension candidates → stem match. Returns a `VaultGraph` with edges keyed by source note paths.

### Note Graph (`note_graph.py`)
`build_note_graph()` performs BFS from a source note through the vault graph, collecting forward edges and backlinks up to the specified depth. `depth=0` returns only the source; `depth=1` returns direct links and backlinks; higher depths traverse recursively. Circular links are handled safely via visited-set tracking.

### Transforms (`transforms.py`)
`to_layered()` reshapes a `VaultGraph` into a `VaultLayered` — a flat BFS depth-layer list where each note appears once at its shallowest reachable depth. Traverses both forward edges and backlinks. Unresolved edges are excluded.

### Link Extraction (`utils.py`)
`_extract_file_links()` uses `obsilink.extract_links()` to parse note content, filtering to `link.is_file` targets only. Each link is converted to a `VaultLink` dataclass for serialization.

### Models (`models.py`)
All models are frozen dataclasses with `slots=True`:
- `VaultIndex` — Scanned vault: `vault_root`, `metadata` (VaultIndexMetadata), `files` (list[VaultFile])
- `VaultFile` — Per-file entry: path, frontmatter, stats, hash, pre-extracted links
- `VaultLink` — Serialized link: type, target, alias, heading, blockid
- `VaultGraph` — Edge dict: `edges[source_note]` → list[LinkEdge]
- `LinkEdge` — Directed edge: link, resolved flag, target_note, unresolved_reason
- `VaultLayered` — BFS depth layers: source_note, metadata, list[LayerEntry]
- `LayerEntry` — Single note at a BFS depth
