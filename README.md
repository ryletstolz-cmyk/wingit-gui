# wingit-gui

`wingit-gui` is a pip-installable Python package that adds a `winget` command which opens a desktop GUI for browsing Winget apps and installing them.

## Install

Preferred (modern packaging):

```bash
pip install .
```

Legacy setup.py install path (also supported):

```bash
python setup.py install
```

## Run

```bash
winget
```

The GUI will:
- Load app data from `winget search --source winget`.
- Show all discovered apps in a searchable table.
- Let you select any app and install it with one click.

## Publish to PyPI

1. Build and validate distributions locally:

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

2. Upload manually (requires a PyPI API token):

```bash
python -m twine upload dist/*
```

3. Or use GitHub Actions Trusted Publishing:
   - Configure your project on https://pypi.org/ to trust this GitHub repository.
   - Create a GitHub Release.
   - The workflow in `.github/workflows/publish-pypi.yml` will build and publish automatically.

## Notes

- Windows only (requires the real `winget` CLI from Microsoft App Installer).
- If `winget` is not available in `PATH`, the app will show a clear error.
