# wingit-gui

`wingit-gui` is a pip-installable Python package that adds a `winget` command which opens a desktop GUI for browsing Winget apps and installing them.

## Install

```bash
pip install .
```

## Run

```bash
winget
```

The GUI will:
- Load app data from `winget search --source winget`.
- Show all discovered apps in a searchable table.
- Let you select any app and install it with one click.

## Notes

- Windows only (requires the real `winget` CLI from Microsoft App Installer).
- If `winget` is not available in `PATH`, the app will show a clear error.
