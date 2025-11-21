# Type Fixer

## Overview
- Formats Python files with `black`, fixes lint issues with `ruff`, and runs `mypy` for type safety.
- Scans every file for missing imports up front so you know which dependencies are absent before linting/type-checking starts.
- Accepts either a single file or a directory (recursively) and can optionally emit a JSON summary of the run.
- Honors `--dry-run` to preview formatting/lint fixes without touching the files.

## Installation
1. Ensure the project dependencies (including `black`, `ruff`, and `mypy`) are installed:
   ```
   pip install .[dev]
   ```
2. Make sure the repo root (or the `type-fixer` folder) is on your `PYTHONPATH` or invoke the script via `python type-fixer/type_fixer.py`.

## Usage
- Format and lint everything under `src/`:
  ```
  python type-fixer/type_fixer.py src/
  ```
- Dry-run to see diffs without editing files:
  ```
  python type-fixer/type_fixer.py src/ --dry-run
  ```
- Save a JSON report (useful for CI logs or dashboards):
  ```
  python type-fixer/type_fixer.py src/ --output reports/type_fixer.json
  ```

## JSON Summary Schema
- `dry_run`: Whether the run avoided mutating files.
- `files_processed`: Absolute paths of every `.py` file inspected.
- `success`: True only if import resolution succeeds and `black`, `ruff`, and `mypy` all exit cleanly.
- `command_results`: Array of `{name, command, return_code, stdout, stderr}` per tool.
- `import_errors`: Array of `{module, files}` entries indicating missing dependencies and where they were referenced.

## Tips
- Keep `pip install .[dev]` up-to-date to ensure `black`, `ruff`, and `mypy` versions stay in sync with `pyproject.toml`.
- For faster runs, point the tool at the smallest directory tree that contains your changes.
