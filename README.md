# GITUX

[![PyPI version](https://img.shields.io/pypi/v/gitux.svg)](https://pypi.org/project/gitux/)
[![Python versions](https://img.shields.io/pypi/pyversions/gitux.svg)](https://pypi.org/project/gitux/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/Hector-2710/gitux/blob/main/LICENSE)

A beautiful, minimalist TUI for Git.

GITUX is a terminal user interface for Git that prioritizes design and user experience. It wraps Git commands in a clean, visually appealing interface — so you can work with Git without leaving the terminal, and enjoy doing it.

## Why GITUX?

Most Git TUIs are functional but not beautiful. GITUX is built with the belief that developer tools should be both powerful and pleasant to look at.

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

**Recommended — with [pipx](https://pipx.pypa.io/) or [uv](https://docs.astral.sh/uv/) (isolated install):**

```bash
# With pipx
pipx install gitux

# Or with uv
uv tool install gitux
```

**Or with pip:**

```bash
pip install gitux
```

> **Requirements:** Python 3.12+ and `git` installed on your system.

<details>
<summary>Install from source (for development)</summary>

```bash
git clone https://github.com/Hector-2710/gitux.git
cd gitux
uv sync --all-extras
uv run gitux
```
</details>

## Usage

Inside any Git repository, just run:

```bash
gitux

# Show version
gitux --version
```

### Keybindings

| Key | Action |
|-----|--------|
| `Tab` | Next section (Files / Diff) |
| `↑` / `↓` or `j` / `k` | Scroll active section |
| `s` / `Enter` | Stage / unstage file |
| `a` / `A` | Stage all / unstage all files |
| `c` | Focus commit message |
| `Ctrl+Enter` | Create commit |
| `Ctrl+p` | Push to remote |
| `r` | Refresh status |
| `b` | Branches panel |
| `l` | Commit log (overlay) |
| `?` | Show help |
| `q` | Quit GITUX |

## Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.12+ | Core runtime |
| TUI | Textual | Terminal interface with CSS styling |
| CLI | Typer | Command-line entry point |
| Git | subprocess + git CLI | Git operations |
| Metrics | psutil | Performance measurement |

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
gitux/
├── src/
│   └── gitux/
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
