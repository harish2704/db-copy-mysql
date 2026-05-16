# db-copy-mysql — Agent Guide

## Project

Single-package Python CLI that copies MySQL databases via `mysqldump`/`mysql` system commands and optional SSH tunnels. **Zero external Python dependencies** — stdlib only.

## Entrypoints

- CLI command: `db-copy-mysql` (registered in `pyproject.toml` / `setup.py` → `db_copy_mysql.__main__:main`)
- Module run: `python -m db_copy_mysql`
- All implementation in `src/db_copy_mysql/db_copy.py` (~1440 lines). `__main__.py` defers to `db_copy.main`.

## Developer Commands

```bash
# install dev deps
pip install -r requirements.txt        # black, flake8, mypy, pytest, pytest-cov

# format — black only, line-length 88 (see pyproject.toml)
black src/ tests/

# lint
flake8 src/ tests/

# typecheck
mypy src/

# test + coverage
pytest tests/ -v --cov=src/db_copy_mysql --cov-report=term-missing

# build
python -m build                         # produces dist/*.tar.gz + *.whl
```

CI validation order (`.github/workflows/ci.yml`): flake8 → `black --check` → mypy → pytest.

## Architecture

`src/db_copy_mysql/`:
- `__init__.py` — exports `DatabaseCopyTool`, `SSHTunnelManager`, `MySQLDumpTool`, `__version__`
- `db_copy.py` — three classes + module-level helpers + `main()`, `load_config_file()`, `create_sample_config()`
  - `_build_ssh_cmd_prefix()` / `_check_remote_tool()` — module-level helpers for remote binary execution
  - `SSHTunnelManager` — spawns `ssh -N -L` subprocess
  - `MySQLDumpTool` — static methods wrapping `mysqldump`/`mysql` subprocesses (all accept optional `ssh_config` param)
  - `DatabaseCopyTool` — orchestrator that wires tunnels → dump → restore → cleanup; accepts `use_binaries_on_source`/`use_binaries_on_target` flags
- `__main__.py` — `from .db_copy import main`

## Testing

- 5 basic mock tests in `tests/test_db_copy.py`
- Tests inject `src/` into sys.path manually (line 13). No conftest or fixtures.
- Test requires no MySQL/SSH — uses `unittest.mock`.

## Gotchas

- **SSH password auth**: `ssh_password` is accepted in config/CLI but **not passed to the SSH command** (the string is stored but never used in the subprocess call). Password-based SSH will fail unless you have `sshpass` or similar set up externally. Use key-based auth (`private_key_path`) instead.
- **`.gitignore` ignores `*.json`**: config files won't be tracked. Use `.json.example` or doc the format.
- **Dump path**: `/tmp/db_dump_<db>_<timestamp>.sql` — default, cleaned up unless `--keep-dump`.
- **`--data-only-safe` mode**: adds missing columns as `TEXT NULL`, imports, then drops them (unless `--keep-temp-cols`).
- **Config key naming change**: JSON config uses `source_ssh`/`target_ssh` keys (with `username`), but `DatabaseCopyTool._setup_tunnel` reads `config['ssh']['host']` and `config['ssh']['username']`. The `main()` function normalizes this: `source_ssh` → `source_config['ssh']`.
- **`--force` in restore**: `mysql --force` is always used, so mysql exit code is 0 even on errors. Error detection relies on stderr parsing.
- **Tests skip MySQL**: they mock `MySQLDumpTool.check_mysql_tools` — don't expect DB connectivity.
- **Remote binary fallback**: `--use-binaries-on-source`/`--use-binaries-on-target` requires SSH config AND the remote tool to be present. If either is missing, the tool warns and falls back to tunnel + local execution.
- **Tool checking is granular**: With `--use-binaries-on-source`, only local `mysql` is checked (not `mysqldump`). With `--use-binaries-on-target`, only local `mysqldump` is checked. If both sides use remote binaries, no local MySQL tools are checked.
- **`_check_remote_tool()` uses `which`**: The remote tool check runs `ssh <opts> which <tool>` on the SSH server. If the tool isn't found, the fallback kicks in.
