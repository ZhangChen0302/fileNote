# Repository Guidelines

## Project Structure & Module Organization

```
fileNote/
├── main.py              # Entry point — CLI dispatch (gui, quick-edit, register, tray)
├── main.legacy.py       # Deprecated code kept for reference
├── ui/
│   └── manager.py       # Main window (CustomTkinter GUI)
├── data/
│   └── store.py         # SQLite data layer, schema & JSON migration
├── registry/
│   └── context_menu.py  # Windows right-click shell registration
├── utils/               # Shared helpers (reserved for growth)
├── build.bat            # PyInstaller packaging script
├── install.bat          # Registers shell menu + creates desktop shortcut
├── filenote.spec         # PyInstaller spec file
└── requirements.txt     # Python dependencies
```

Source code lives in `ui/`, `data/`, `registry/`, and `utils/`. No separate test directory exists yet — if you add tests, place them in a `tests/` folder at the root using `pytest`.

## Build, Test, and Development Commands

| Command | Purpose |
|---|---|
| `python main.py` | Launch the manager window |
| `python main.py --gui "C:\path"` | Open manager pointed at a specific path |
| `python main.py --quick "C:\path"` | Quick-edit popup for a single file (used by shell menu) |
| `python main.py --register` | Register Windows context-menu entries (requires admin) |
| `python main.py --unregister` | Remove context-menu entries |
| `build.bat` | Package into `dist/FileNote/` via PyInstaller |
| `install.bat` | Register context menu + create desktop shortcut |

Install dependencies with:
```bash
pip install -r requirements.txt
```

## Coding Style & Naming Conventions

- **Python 3.10+** — type hints are encouraged (e.g., `str | None`).
- **4-space indentation**, no tabs.
- **Naming**: `snake_case` for functions and variables, `PascalCase` for classes, `UPPER_SNAKE` for constants.
- **Logging**: use `loguru` (`from loguru import logger`) — not the standard `logging` module.
- Keep module-level docstrings in Chinese to match existing code.
- No formatter or linter is configured; follow PEP 8 conventions by hand.

## Testing Guidelines

No formal test suite exists yet. When adding tests:

- Use **pytest** and place files in `tests/` with the naming pattern `test_<module>.py`.
- Run tests with `pytest tests/`.
- Mock SQLite and GUI dependencies to keep tests headless.

## Commit & Pull Request Guidelines

Git history uses **Conventional Commits** in Chinese:

```
feat: 添加文件分类功能和文件实际时间显示
fix: 修复文件类型分类筛选和图标偏移
```

- Prefix each message with `feat:`, `fix:`, `refactor:`, or `docs:`.
- Keep the subject line under 72 characters.
- For pull requests: describe what changed and why, link related issues, and include screenshots for UI changes.

## Security & Configuration Tips

- The database is stored at `%LOCALAPPDATA%\FileNote\notes.db` — never commit `.db` files.
- Context-menu registration writes to the Windows registry; always test `--register` / `--unregister` in a VM or dev environment first.
- The packaged executable sets `console=True` in the spec for error visibility; change to `False` for release builds.
