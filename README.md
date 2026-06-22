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

---

[![PyPI](https://img.shields.io/pypi/v/OASYS2-BARC-EXTENSIONS.svg)]([https://pypi.org/project/barc4beams/](https://pypi.org/project/OASYS2-BARC-EXTENSIONS/))
[![License: CeCILL-2.1](https://img.shields.io/badge/license-CeCILL--2.1-blue.svg)](https://opensource.org/licenses/CECILL-2.1)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20793381.svg)](https://doi.org/10.5281/zenodo.20793381)
