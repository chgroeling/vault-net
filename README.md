# link-tracer

`link-tracer` is a Python package for tracing links in Obsidian notes back to source files in a vault. It targets two output modes:

- CLI output as JSON
- Python API output as a dictionary

## Development setup

```bash
uv sync --all-extras
```

## Quality checks

```bash
uv run ruff format src tests
uv run ruff check src tests
uv run mypy src
uv run pytest
```

## CLI

The CLI entry point is wired and currently acts as a stub:

```bash
uv run link-tracer --help
```

## Project layout

```text
.
├── pyproject.toml
├── src/
│   └── link_tracer/
│       ├── __init__.py
│       ├── api.py
│       ├── cli.py
│       └── models.py
├── tests/
│   └── test_core.py
└── docs/
    └── index.md
```

## License

MIT. See `LICENSE`.
