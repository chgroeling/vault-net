# link-tracer

`link-tracer` is a Python project intended to trace links found in Obsidian markdown notes
back to note files on disk.

## Scope

The initialized project supports:

- package import and version metadata
- a stub CLI entry point (`link-tracer`)
- typed data models for future trace results
- a stub API boundary for future implementation

Tracing behavior is not implemented yet.

## Planned output contract

The project is prepared for a structured trace graph output containing:

- visited note nodes
- link edges between notes
- unresolved or invalid link errors
- traversal options and summary counts

## Development

```bash
uv sync --all-extras
uv run pytest
```
