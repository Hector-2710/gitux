<h1 align="center">gitux</h1>

<p align="center">
  <img src="assets/gitux-2.png" alt="gitux logo" width="220"/>
</p>

<p align="center">
  <em>A beautiful, minimalist TUI for Git.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/gitux/"><img src="https://img.shields.io/pypi/v/gitux.svg" alt="PyPI version"/></a>
  <a href="https://pypi.org/project/gitux/"><img src="https://img.shields.io/pypi/pyversions/gitux.svg" alt="Python versions"/></a>
  <a href="https://github.com/Hector-2710/gitux/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"/></a>
  <img src="https://img.shields.io/badge/status-beta-purple.svg" alt="Status: Beta"/>
</p>

<p align="center">
  <b>Git in the terminal — A beautiful, minimalist TUI for Git..</b>
</p>

---

gitux is a terminal user interface for Git that prioritizes **design** and
**user experience**. It wraps Git commands in a clean, visually appealing
interface — so you can work with Git without leaving the terminal, and enjoy
doing it.

## ✨ Demo

Soon

```
$ gitux
```

## 🎯 Why gitux?

Most Git TUIs are functional but not beautiful. gitux is built with the belief
that developer tools should be both **powerful** and **pleasant to look at**.

| Pillar | What it means |
|--------|---------------|
| 🪶 **Minimalist** | No clutter, no overwhelming menus. Just what you need. |
| 🎨 **Beautiful** | Clean colors, thoughtful spacing, modern aesthetics. |
| ⚡ **Fast** | Direct subprocess calls to Git, no heavy abstractions. |

> **Honest comparison:** gitux is not trying to replace `lazygit` or `tig` as a
> full-featured power tool. It is a focused, opinionated interface for the
> everyday Git workflow — status, staging, commits, branches, and pushes —
> designed to be a pleasure to use.

## 🚀 Features

| Feature | Description |
|---------|-------------|
| 📂 **Repository status** | Color-coded file states (staged / unstaged / modified / added / deleted) |
| 🕘 **Commit history** | Browse commits with a visual graph and branch refs |
| ✍️ **Stage & commit** | Stage files individually or all at once, write commit messages |
| 🔍 **Diff viewer** | Side-by-side diffs with line numbers and syntax-aware colors |
| 🌿 **Branch management** | Create, switch, and delete branches |
| 🔀 **Merge** | Merge branches from the interface |
| 🚀 **Push** | Push to remote with porcelain output parsing |
| 📊 **Performance metrics** | Startup time and memory usage tracking |

## 📦 Installation

**Requirements:** Python 3.12+ and `git` installed on your system.

### Recommended — isolated install

```bash
# With pipx
pipx install gitux

# Or with uv
uv tool install gitux
```

### With pip

```bash
pip install gitux
```

## 🖥️ Usage

Inside any Git repository, just run:

```bash
gitux

# Show version
gitux --version
```

### ⌨️ Keybindings

| Key | Action |
|-----|--------|
| `Tab` | Next section (Files / Diff) |
| `↑` / `↓` or `j` / `k` | Scroll active section |
| `s` / `Enter` | Stage / unstage file |
| `a` / `A` | Stage all / unstage all files |
| `c` | Open commit screen |
| `Ctrl+Enter` | Create commit |
| `Ctrl+p` | Push to remote |
| `r` | Refresh status |
| `b` | Branches panel |
| `l` | Commit log (overlay) |
| `?` | Show help |
| `q` | Quit Gitux |

## 🧱 Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.12+ | Core runtime |
| TUI | Textual | Terminal interface with CSS styling |
| CLI | Typer | Command-line entry point |
| Git | subprocess + git CLI | Git operations |
| Metrics | psutil | Performance measurement |

## 🛠️ Development

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

## 📁 Project Structure

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
│   ├── STYLE_GUIDE.md          # Brand & visual identity guide
│   ├── context.md
│   ├── container.md
│   └── diagrams/
├── pyproject.toml
└── README.md
```

## 🤝 Contributing

Contributions are welcome! Feel free to open an
[issue](https://github.com/Hector-2710/gitux/issues) or a
[pull request](https://github.com/Hector-2710/gitux/pulls).

Before contributing, please read the
[style guide](docs/STYLE_GUIDE.md) to keep the visual identity consistent.

## 📄 License

[MIT](LICENSE) © Hector-2710