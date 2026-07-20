# GITZ

A beautiful, minimalist TUI for Git.

GITZ is a terminal user interface for Git that prioritizes design and user experience. It wraps Git commands in a clean, visually appealing interface — so you can work with Git without leaving the terminal, and enjoy doing it.

## Why GITZ?

Most Git TUIs are functional but not beautiful. GITZ is built with the belief that developer tools should be both powerful and pleasant to look at.

- **Minimalist** — No clutter, no overwhelming menus. Just what you need.
- **Beautiful** — Clean colors, thoughtful spacing, modern aesthetics.
- **Fast** — Direct subprocess calls to Git, no heavy abstractions.

## Features

- View repository status with color-coded file states
- Browse commit history with details
- Stage and commit files with messages
- View diffs between files
- Manage branches (create, switch, delete)
- Merge branches
- Push to remote
- Performance metrics (startup time, memory usage)

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/gitz.git
cd gitz

# Install with uv
uv sync

# Run
uv run gitz
```

## Usage

```bash
# Launch the TUI
uv run gitz

# Show version
uv run gitz --version
```

## Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.12+ | Core runtime |
| TUI | Textual | Terminal interface with CSS styling |
| CLI | Typer | Command-line entry point |
| Git | subprocess + git CLI | Git operations |
| Metrics | psutil | Performance measurement |

## Architecture

GITZ follows a layered architecture:

```
┌─────────────────────────────────────────────────┐
│                   GITZ                          │
│                                                 │
│   ┌──────────┐   ┌──────────────┐   ┌────────┐ │
│   │   TUI    │──▶│ Git Infra.   │──▶│  Git   │ │
│   │(Textual) │◀──│(subprocess)  │◀──│(externo)│ │
│   └──────────┘   └──────────────┘   └────────┘ │
│        │                                        │
│        ▼                                        │
│   ┌──────────┐                                  │
│   │ Metrics  │                                  │
│   │ (psutil) │                                  │
│   └──────────┘                                  │
└─────────────────────────────────────────────────┘
```

- **TUI** — Renders the interface, handles keyboard input
- **Git Infrastructure** — Executes Git commands via subprocess
- **Metrics** — Measures startup time, memory, CPU usage

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run linter
uv run ruff check .

# Format code
uv run ruff format .
```

## Project Structure

```
gitz/
├── src/
│   └── gitz/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py              # Typer entry point
│       ├── domain/             # Data models
│       ├── git/                # Git infrastructure
│       ├── presenter/          # Business logic
│       ├── ui/                 # Textual TUI
│       ├── metrics/            # Performance metrics
│       └── utils/              # Config, exceptions
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── context.md
│   ├── container.md
│   └── diagrams/
├── pyproject.toml
└── README.md
```

## License

MIT
