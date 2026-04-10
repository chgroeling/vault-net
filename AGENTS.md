# AGENTS.md

## Project Description

`vault-net` is a CLI and Python library that scans an Obsidian vault, resolves internal links to files in the vault,
and exposes index and graph representations through both programmatic APIs and CLI output formats.

## Layered Architecture

This project uses a clean, layered architecture with strict dependency direction:

```text
Outer layers can depend on inner layers.
Inner layers must never depend on outer layers.

interface -> application -> domain
infrastructure -> domain
```

### Dependency Rule (non-negotiable)

- Domain must not import from application, interface, or infrastructure.
- Application must not import from interface or infrastructure implementations.
- Infrastructure may implement domain protocols and use third-party libraries.
- Interface (CLI) composes concrete adapters and invokes application use cases.

## Source Layout

```text
.
├── AGENTS.md
├── README.md
├── src/
│   └── vault_net/
│       ├── application/
│       │   └── use_cases/
│       ├── domain/
│       │   └── services/
│       ├── infrastructure/
│       │   ├── graph/
│       │   └── scanner/
│       └── interface/
│           ├── cli/
│           └── formatters/
└── tests/
    ├── domain/
    ├── infrastructure/
    ├── integration/
    └── interface/
```

## Layer Responsibilities

### Domain

- Contains pure entities and business rules.
- No library-specific behavior should leak into domain entities.
- Protocols define required behavior (`VaultScanner`, `GraphBuilder`) without binding to concrete tools.

### Application

- Contains orchestration logic as use cases.
- Receives dependencies via constructor injection.
- Coordinates domain services and ports, but does not parse CLI or call third-party libraries directly.

### Infrastructure

- Implements domain protocols using third-party dependencies (`matterify`, `obsilink`, `networkx`).
- Converts external objects into domain models.

### Interface

- Handles user interaction and output formatting.
- Instantiates concrete infrastructure adapters and calls application use cases.
- Should be thin: validate input, invoke use case, render output.

## Import Rules

- Allowed:
  - `vault_net.interface.*` -> `vault_net.application.*`, `vault_net.domain.*`
  - `vault_net.infrastructure.*` -> `vault_net.domain.*`
  - `vault_net.application.*` -> `vault_net.domain.*`
- Forbidden:
  - `vault_net.domain.*` -> anything outside `vault_net.domain.*`
  - `vault_net.application.*` -> `vault_net.infrastructure.*` (except in `application/api.py`, which is the package facade)

## Naming Conventions

- Prefer domain terms in domain/application function names (for example: `full_graph`, `neighborhood_graph`, `index`).
- Avoid infrastructure or library terms in domain/application names (for example: `networkx`, `digraph`, `ego`).
- Keep infrastructure-specific names only in infrastructure adapters (for example: `NetworkXGraphBuilder`).
- Use use-case class names in `VerbNounUseCase` form (for example: `BuildFullGraphUseCase`).
- Keep use-case module names aligned with class names and responsibility (for example: `build_full_graph.py`).
- Name service modules after their service role (for example: `vault_registry.py`, `slug_service.py`).

## Testing Strategy

- Unit tests focus on one layer at a time.
- Application tests should use fakes/mocks for domain ports.
- Infrastructure tests validate adapter behavior against real third-party integrations.
- CLI tests verify command behavior and output formatting.

### Test Layout

```text
tests/
├── domain/
│   └── services/
├── infrastructure/
│   ├── graph/
│   └── scanner/
├── integration/
│   └── obsilink/
└── interface/
```

## Rules

- Use skill `python-code-style` and `python-design-patterns` before adding/modifying python code.
- Use skill `python-testing-patterns` before adding/modifying pytest suites.
- Keep code ASCII by default.
- Prefer explicit, simple composition over meta-framework abstractions.
- Do not introduce layer-crossing imports for convenience.

## Workflows

- Dependency management: `uv lock`, `uv sync --all-extras`, `uv add`, `uv remove`.
- Run CLI locally: `uv run python -m vault_net --help`.
- Packaging: `uv build`.

## Quality Gate

Run before completing a change:

`uv run ruff format src tests && uv run ruff check src tests && uv run mypy src tests && uv run pytest`
