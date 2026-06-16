# OASYS2-BARC-EXTENSIONS

OASYS2 extension widgets for BARC projects.

This repository starts as a minimal SHADOW4 extension package, following the
institutional extension pattern used by `OASYS2-ESRF-EXTENSIONS`.

## Current Scope

- Register a `BARC Shadow4` widget category in OASYS2.
- Provide package placeholders for future `barc4beams` and `barc4shadow`
  integration.
- Keep the initial skeleton intentionally small for the first commit.

Future categories such as SYNED or SRW can be added later by extending the
`orangecontrib.barc` package and adding new `oasys2.widgets` entry points.

## Developer Install

Use the Python environment used by OASYS2:

```bash
python -m pip install -e . --no-deps --no-binary :all:
```

Restart OASYS2 after installation.
