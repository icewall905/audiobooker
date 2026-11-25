"""Console reporting shared by the local and remote command line interfaces."""

from __future__ import annotations

import sys
from typing import Dict, Optional, TextIO

from .pipeline import JobResult


class ConsoleReporter:
    """Prints job progress without flooding the terminal."""

    def __init__(self, quiet: bool = False, stream: Optional[TextIO] = None):
        self.quiet = quiet
        self.stream = stream or sys.stdout
        self._last_group: Optional[str] = None

    def header(self, title: str, fields: Dict[str, object]) -> None:
        self.stream.write(f"=== {title} ===\n")
        for label, value in fields.items():
            self.stream.write(f"{label}: {value}\n")
        self.stream.write("=" * 50 + "\n")
        self.stream.flush()

    def log(self, message: str) -> None:
        if self.quiet:
            return
        self.stream.write(message + "\n")
        self.stream.flush()

    def progress(self, done: int, total: int, message: str) -> None:
        if self.quiet:
            return
        group = message.rsplit(":", 1)[0]
        if group == self._last_group:
            return
        self._last_group = group
        percent = 100.0 * done / max(total, 1)
        self.stream.write(f"[{done:>4}/{total} {percent:5.1f}%] {message}\n")
        self.stream.flush()

    def result(self, result: JobResult) -> None:
        for line in result.summary_lines():
            self.stream.write(line + "\n")
        if result.failures:
            self.stream.write("\n   Failed chunks (text missing from the output):\n")
            for failure in result.failures[:20]:
                self.stream.write(f"     - {failure.describe()}\n")
            if len(result.failures) > 20:
                self.stream.write(f"     ... and {len(result.failures) - 20} more\n")
            self.stream.write(
                "   Re-run the same command to re-render only the failed sections.\n"
            )
        self.stream.flush()
