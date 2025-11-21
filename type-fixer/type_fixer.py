"""
Command line helper that keeps Python modules lint- and type-clean.

The tool wraps three best-of-class utilities:

* black – for deterministic formatting that removes a large class of lint errors.
* ruff  – for lint detection and auto-fixes (`ruff check --fix`).
* mypy  – for static type validation (optionally auto-installs missing stub packages).

Author: Christian Amauger
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import logging
import shutil
import subprocess
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FixerConfig:
    """Runtime configuration for the fixer."""

    input_path: Path
    output_path: Path | None
    dry_run: bool


@dataclass(frozen=True)
class CommandResult:
    """Outcome of running an external tool."""

    name: str
    command: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.return_code == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": list(self.command),
            "return_code": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


@dataclass(frozen=True)
class ImportErrorDetail:
    """Metadata describing a missing import discovered in the target source."""

    module: str
    files: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "files": list(self.files),
        }


@dataclass(frozen=True)
class FixSummary:
    """Serializable report describing what the fixer did."""

    files_processed: tuple[str, ...]
    command_results: tuple[CommandResult, ...]
    import_errors: tuple[ImportErrorDetail, ...]
    dry_run: bool

    @property
    def success(self) -> bool:
        return not self.import_errors and all(result.success for result in self.command_results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "files_processed": list(self.files_processed),
            "success": self.success,
            "command_results": [result.to_dict() for result in self.command_results],
            "import_errors": [error.to_dict() for error in self.import_errors],
        }

    def write(self, destination: Path) -> None:
        destination = destination.expanduser()
        if destination.exists() and destination.is_dir():
            file_path = destination / "type_fixer_report.json"
        else:
            file_path = destination
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


class PythonFileFixer:
    """Coordinates formatting, linting, and type-checking for Python modules."""

    def __init__(self, config: FixerConfig) -> None:
        self._config = config
        self._input_path = config.input_path.expanduser().resolve(strict=False)
        self._files = tuple(self._discover_python_files())
        self._target_arguments = self._build_target_arguments()
        self._spec_cache: dict[str, bool] = {}

    def run(self) -> FixSummary:
        if not self._files:
            raise ValueError(f"No Python files found under {self._input_path}")

        logger.info("Found %s Python file(s) to process", len(self._files))

        import_errors = self._check_import_errors()

        command_results = [
            self._format_with_black(),
            self._lint_with_ruff(),
            self._type_check_with_mypy(),
        ]

        summary = FixSummary(
            files_processed=tuple(str(path) for path in self._files),
            command_results=tuple(command_results),
            import_errors=import_errors,
            dry_run=self._config.dry_run,
        )

        if self._config.output_path:
            summary.write(self._config.output_path)
            logger.info("Summary written to %s", self._config.output_path)

        return summary

    def _discover_python_files(self) -> tuple[Path, ...]:
        path = self._input_path
        if not path.exists():
            raise FileNotFoundError(f"Input path '{path}' does not exist.")

        if path.is_file():
            if path.suffix != ".py":
                raise ValueError(f"Input file '{path}' is not a Python file.")
            return (path.resolve(),)

        files = sorted(
            p.resolve()
            for p in path.rglob("*.py")
            if "__pycache__" not in p.parts and not self._is_hidden(p)
        )
        return tuple(files)

    def _build_target_arguments(self) -> tuple[str, ...]:
        path = self._input_path
        if path.is_file():
            return (str(path),)
        return (str(path),)

    def _check_import_errors(self) -> tuple[ImportErrorDetail, ...]:
        module_to_files: dict[str, set[str]] = defaultdict(set)
        for path in self._files:
            for module in self._collect_import_modules(path):
                module_to_files[module].add(str(path))

        missing: list[ImportErrorDetail] = []
        for module, files in sorted(module_to_files.items()):
            if self._module_is_available(module):
                continue
            detail = ImportErrorDetail(module=module, files=tuple(sorted(files)))
            missing.append(detail)
            logger.error(
                "Import error: module '%s' referenced in %s could not be resolved.",
                module,
                ", ".join(files),
            )

        if missing:
            logger.warning(
                "Detected %s missing import(s). Install the required dependencies and re-run.",
                len(missing),
            )

        return tuple(missing)

    def _collect_import_modules(self, file_path: Path) -> set[str]:
        try:
            source = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("Unable to read %s: %s", file_path, exc)
            return set()

        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            logger.warning("Skipping import scan for %s (syntax error: %s)", file_path, exc)
            return set()

        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add(alias.name.split(".", 1)[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level != 0 or not node.module:
                    continue
                modules.add(node.module.split(".", 1)[0])
        return modules

    def _module_is_available(self, module: str) -> bool:
        if not module:
            return True
        if module in sys.builtin_module_names:
            return True
        cached = self._spec_cache.get(module)
        if cached is not None:
            return cached
        spec = importlib.util.find_spec(module)
        available = spec is not None
        self._spec_cache[module] = available
        return available

    @staticmethod
    def _is_hidden(path: Path) -> bool:
        return any(part.startswith(".") for part in path.parts if part not in (".", ".."))

    def _format_with_black(self) -> CommandResult:
        args = ["black"]
        if self._config.dry_run:
            args.extend(["--check", "--diff"])
        args.extend(self._target_arguments)
        return self._run_command("black", args)

    def _lint_with_ruff(self) -> CommandResult:
        args = ["ruff", "check"]
        if self._config.dry_run:
            args.append("--diff")
        else:
            args.append("--fix")
        args.extend(self._target_arguments)
        return self._run_command("ruff", args)

    def _type_check_with_mypy(self) -> CommandResult:
        args = [
            "mypy",
            "--hide-error-context",
            "--show-error-codes",
            "--no-color-output",
        ]
        if not self._config.dry_run:
            args.extend(["--install-types", "--non-interactive"])
        args.extend(self._target_arguments)
        return self._run_command("mypy", args)

    def _run_command(self, name: str, args: Sequence[str]) -> CommandResult:
        executable = args[0]
        self._ensure_executable_available(executable)
        logger.info("Running %s: %s", name, " ".join(args))

        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
        )

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()

        if stdout:
            logger.debug("%s stdout:\n%s", name, stdout)
        if stderr:
            logger.debug("%s stderr:\n%s", name, stderr)

        return CommandResult(
            name=name,
            command=tuple(args),
            return_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
        )

    @staticmethod
    def _ensure_executable_available(executable: str) -> None:
        if shutil.which(executable) is None:
            raise FileNotFoundError(
                f"Required executable '{executable}' is not available on PATH. "
                "Install the 'dev' extras (pip install .[dev]) or add the tool manually."
            )


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Automatically fix lint errors and report type issues for Python files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Python file or directory to process.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON file to write a summary report to.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the operations without modifying any files.",
    )

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity.",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(levelname)s: %(message)s",
    )

    try:
        config = FixerConfig(
            input_path=args.input,
            output_path=args.output,
            dry_run=args.dry_run,
        )
        fixer = PythonFileFixer(config)
        summary = fixer.run()

        for result in summary.command_results:
            level = logging.INFO if result.success else logging.ERROR
            logger.log(
                level,
                "%s exited with %s",
                result.name,
                "success" if result.success else f"code {result.return_code}",
            )

        if summary.success:
            logger.info("All tools completed successfully.")
            return 0

        logger.error("One or more tools reported issues. See logs above for details.")
        return 1

    except Exception as exc:  # noqa: BLE001 - top-level guard
        logger.error("Error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
