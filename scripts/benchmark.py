"""External performance benchmark for GITUX.

Usage:
    uv run python scripts/benchmark.py

Measures:
    - Git operation latency (status, diff, rev-parse, etc.)
    - Real app startup time via Textual headless mode
    - Peak memory (background sampling)
    - CPU usage during operations (background sampling)
"""

import asyncio
import datetime
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import psutil

PROJECT_ROOT = Path(__file__).resolve().parent.parent
METRICS_DIR = PROJECT_ROOT / "docs" / "metrics"
WARMUP_RUNS = 2
MONITOR_INTERVAL = 0.05  # seconds between resource samples


@dataclass
class GitOpResult:
    name: str
    command: str
    elapsed_ms: float
    success: bool


@dataclass
class BenchmarkResult:
    git_ops: list[GitOpResult] = field(default_factory=list)
    startup_ms: float = 0.0
    peak_memory_mb: float = 0.0
    max_cpu_percent: float = 0.0
    avg_cpu_percent: float = 0.0
    cpu_samples_count: int = 0
    total_duration_ms: float = 0.0
    warmup_runs: int = 0
    repo_name: str = ""
    repo_path: str = ""
    version: str = ""
    git_commit: str = ""
    git_branch: str = ""
    timestamp: str = ""


#  RESOURCE MONITOR
class ResourceMonitor:
    """Background thread that continuously samples CPU and memory.

    Must call start() before the measured section and stop() after.
    psutil.cpu_percent() is primed in start() so the first real sample
    is meaningful (first unprimed call always returns 0.0).
    """

    def __init__(self, interval: float = MONITOR_INTERVAL):
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.peak_memory_mb: float = 0.0
        self._cpu_samples: list[float] = []

    def start(self) -> None:
        """Prime the CPU counter and start the background thread."""
        psutil.Process().cpu_percent(interval=None)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        proc = psutil.Process()
        while not self._stop.is_set():
            mem_mb = proc.memory_info().rss / (1024 * 1024)
            if mem_mb > self.peak_memory_mb:
                self.peak_memory_mb = mem_mb
            cpu = proc.cpu_percent(interval=None)
            self._cpu_samples.append(cpu)
            self._stop.wait(self.interval)

    def stop(self) -> None:
        """Stop monitoring and wait for the thread to finish."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    @property
    def max_cpu_percent(self) -> float:
        return max(self._cpu_samples) if self._cpu_samples else 0.0

    @property
    def avg_cpu_percent(self) -> float:
        if not self._cpu_samples:
            return 0.0
        return sum(self._cpu_samples) / len(self._cpu_samples)

    @property
    def samples_count(self) -> int:
        return len(self._cpu_samples)


#  MEASUREMENT HELPERS
def _run_git_timed(args: list[str], timeout: int = 30) -> GitOpResult:
    """Run a git command and measure its execution time."""
    cmd_str = "git " + " ".join(args)
    start = time.perf_counter()
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = (time.perf_counter() - start) * 1000
        return GitOpResult(
            name=args[0],
            command=cmd_str,
            elapsed_ms=elapsed,
            success=result.returncode == 0,
        )
    except subprocess.TimeoutExpired:
        elapsed = (time.perf_counter() - start) * 1000
        return GitOpResult(
            name=args[0], command=cmd_str, elapsed_ms=elapsed, success=False
        )
    except FileNotFoundError:
        elapsed = (time.perf_counter() - start) * 1000
        return GitOpResult(
            name=args[0], command=cmd_str, elapsed_ms=elapsed, success=False
        )


def _get_repo_info() -> tuple[str, str]:
    """Get repo name and path."""
    name = "unknown"
    path = "."
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            name = Path(path).name
    except Exception:
        pass
    return name, path


def _get_version() -> str:
    """Get app version from __init__.py."""
    init_file = PROJECT_ROOT / "src" / "gitux" / "__init__.py"
    try:
        content = init_file.read_text()
        for line in content.splitlines():
            if "__version__" in line:
                return line.split("=")[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "unknown"


def _get_git_commit() -> str:
    """Get current git commit short hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _get_git_branch() -> str:
    """Get current git branch."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


#  BENCHMARK SUITE
_GIT_OPS = [
    (["status", "--porcelain=v1", "-z"], "status"),
    (["rev-parse", "--abbrev-ref", "HEAD"], "rev-parse (branch)"),
    (["rev-parse", "--show-toplevel"], "rev-parse (toplevel)"),
    (["diff"], "diff (unstaged)"),
    (["diff", "--cached"], "diff (staged)"),
    (["remote"], "remote (list)"),
    (["rev-list", "--left-right", "--count", "HEAD...@{upstream}"], "rev-list (ahead/behind)"),
]


def _warmup_git_operations(runs: int) -> None:
    """Run git operations without recording to prime filesystem cache."""
    for _ in range(runs):
        for args, _ in _GIT_OPS:
            _run_git_timed(args)


def benchmark_git_operations() -> list[GitOpResult]:
    """Time all git operations that GITUX uses (single measured run)."""
    results = []
    for args, name in _GIT_OPS:
        result = _run_git_timed(args)
        result.name = name
        results.append(result)
    return results


async def _run_app_headless() -> None:
    """Run GituxApp in Textual headless mode (for startup measurement)."""
    from gitux.ui.app import GituxApp

    app = GituxApp()
    async with app.run_test(headless=True) as pilot:
        await pilot.pause()  # ensure first render completes before exiting


def _benchmark_startup() -> float:
    """Measure real app startup time using Textual's headless mode.

    Measures the full lifecycle: imports → constructor → CSS parsing →
    widget mounting → on_mount() → first render → shutdown.
    """
    start = time.perf_counter()
    try:
        asyncio.run(_run_app_headless())
    except Exception as exc:
        print(f"  WARNING: Startup measurement failed: {exc}")
    elapsed = (time.perf_counter() - start) * 1000
    return elapsed


def benchmark_full_session() -> BenchmarkResult:
    """Run the full benchmark suite."""
    result = BenchmarkResult()
    result.warmup_runs = WARMUP_RUNS

    # Metadata
    result.repo_name, result.repo_path = _get_repo_info()
    result.version = _get_version()
    result.git_commit = _get_git_commit()
    result.git_branch = _get_git_branch()
    result.timestamp = datetime.datetime.now().isoformat()

    session_start = time.perf_counter()

    # Warm-up: prime filesystem cache before monitoring
    print("  Warming up git operations...")
    _warmup_git_operations(WARMUP_RUNS)

    # Start resource monitoring (CPU + memory sampled every 50ms)
    monitor = ResourceMonitor()
    monitor.start()

    # Benchmark git operations
    print("  Measuring git operations...")
    result.git_ops = benchmark_git_operations()

    # Startup time (includes on_mount → git ops inside the app)
    print("  Measuring app startup time...")
    result.startup_ms = _benchmark_startup()

    # Stop monitoring
    monitor.stop()

    # Collect resource metrics
    result.peak_memory_mb = monitor.peak_memory_mb
    result.max_cpu_percent = monitor.max_cpu_percent
    result.avg_cpu_percent = monitor.avg_cpu_percent
    result.cpu_samples_count = monitor.samples_count

    result.total_duration_ms = (time.perf_counter() - session_start) * 1000

    return result


#  REPORT GENERATION
def generate_report(result: BenchmarkResult) -> str:
    """Generate markdown report from benchmark results."""
    lines = []

    lines.append("# GITUX Performance Report")
    lines.append("")
    lines.append("## Metadata")
    lines.append("")
    lines.append(f"- **Version:** {result.version}")
    lines.append(f"- **Git commit:** {result.git_commit}")
    lines.append(f"- **Git branch:** {result.git_branch}")
    lines.append(f"- **Repository:** {result.repo_name} ({result.repo_path})")
    lines.append(f"- **Generated:** {result.timestamp}")
    lines.append(f"- **Duration:** {result.total_duration_ms:.1f}ms")
    lines.append(f"- **Warm-up runs:** {result.warmup_runs}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Startup time (Textual) | {result.startup_ms:.1f} ms |")
    lines.append(f"| Git operations | {len(result.git_ops)} |")
    lines.append(f"| Peak memory | {result.peak_memory_mb:.1f} MB |")
    lines.append(f"| Max CPU | {result.max_cpu_percent:.1f}% |")
    lines.append(f"| Avg CPU | {result.avg_cpu_percent:.1f}% |")
    lines.append(f"| CPU samples | {result.cpu_samples_count} |")
    lines.append("")

    # Git Operations
    lines.append("## Git Operations")
    lines.append("")
    lines.append("| Operation | Time (ms) | Status |")
    lines.append("|-----------|----------:|--------|")
    for op in result.git_ops:
        status = "✓" if op.success else "✗"
        lines.append(f"| {op.name} | {op.elapsed_ms:.1f} | {status} |")
    lines.append("")

    # Performance Analysis
    lines.append("## Performance Analysis")
    lines.append("")
    if result.git_ops:
        fastest = min(result.git_ops, key=lambda x: x.elapsed_ms)
        slowest = max(result.git_ops, key=lambda x: x.elapsed_ms)
        avg_time = sum(op.elapsed_ms for op in result.git_ops) / len(result.git_ops)
        lines.append(f"- **Fastest operation:** {fastest.name} ({fastest.elapsed_ms:.1f}ms)")
        lines.append(f"- **Slowest operation:** {slowest.name} ({slowest.elapsed_ms:.1f}ms)")
        lines.append(f"- **Average git op time:** {avg_time:.1f}ms")
        lines.append(
            f"- **Total git time:** {sum(op.elapsed_ms for op in result.git_ops):.1f}ms"
        )
    lines.append("")

    # Resource Usage
    lines.append("## Resource Usage")
    lines.append("")
    lines.append(f"- **Peak memory:** {result.peak_memory_mb:.1f} MB")
    lines.append(f"- **Max CPU:** {result.max_cpu_percent:.1f}%")
    lines.append(f"- **Avg CPU:** {result.avg_cpu_percent:.1f}%")
    lines.append(f"- **CPU samples collected:** {result.cpu_samples_count}")
    lines.append("")

    return "\n".join(lines) + "\n"


#  MAIN
def main():
    print("GITUX Performance Benchmark")
    print("=" * 40)

    result = benchmark_full_session()

    report = generate_report(result)

    # Create docs/metrics/ directory if it doesn't exist
    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate filename: v{version}_{date}_{time}_{commit}.md
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    version = result.version.replace(".", "-")
    commit = result.git_commit
    filename = f"v{version}_{date_str}_{time_str}_{commit}.md"

    filepath = METRICS_DIR / filename
    filepath.write_text(report, encoding="utf-8")

    print(f"\nReport saved to: {filepath}")


if __name__ == "__main__":
    main()
