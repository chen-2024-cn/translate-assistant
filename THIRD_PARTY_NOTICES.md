# Third-party notices

Project code is licensed under GPL-3.0-only; see `LICENSE`. Third-party components retain their own licenses and notices. The table below describes the pinned Windows build environment, not a relicensing of its dependencies.

PyQt5 is used under its GPL v3 distribution. Qt modules included by PyQt5-Qt5 have their own LGPL/GPL and third-party terms; review the actual binaries and upstream Qt sources before redistribution. Keep license texts and applicable corresponding-source obligations with released executables. This document does not replace those obligations.

PyInstaller has a GPL license with a bootloader exception; using it does not by itself require an application to be GPL. Its license and exception are copied under `third_party/licenses`. Python and Windows speech components have separate terms; Windows components are not supplied by this repository.

| Component | Pinned version | License metadata | Use |
|---|---|---|---|
| altgraph | 0.17.5 | MIT | Build only |
| beautifulsoup4 | 4.15.0 | MIT License | Runtime |
| certifi | 2026.7.22 | MPL-2.0 | Runtime |
| charset-normalizer | 3.4.9 | MIT | Runtime |
| deep-translator | 1.11.4 | MIT | Runtime |
| idna | 2.10 | BSD-like | Runtime |
| packaging | 26.2 | Apache-2.0 OR BSD-2-Clause | Build only |
| pefile | 2024.8.26 | MIT | Build only |
| pyinstaller | 6.21.0 | GPLv2-or-later with a special exception which allows to use PyInstaller to build and distribute non-free programs (including commercial ones) | Build only |
| pyinstaller-hooks-contrib | 2026.6 | See upstream license files | Build only |
| pyperclip | 1.11.0 | BSD | Runtime |
| PyQt5 | 5.15.11 | GPL v3 | Runtime |
| PyQt5-Qt5 | 5.15.2 | LGPL v3 | Runtime |
| PyQt5_sip | 12.19.0 | BSD-2-Clause | Runtime |
| pywin32 | 312 | PSF | Runtime |
| pywin32-ctypes | 0.2.3 | BSD-3-Clause | Build only |
| requests | 2.34.2 | Apache-2.0 | Runtime |
| setuptools | 83.0.0 | MIT | Build only |
| soupsieve | 2.9.1 | MIT | Runtime |
| typing_extensions | 4.16.0 | PSF-2.0 | Runtime |
| urllib3 | 2.7.0 | MIT | Runtime |

## License materials and upstream projects

Wheel-provided license/notice files are preserved under `third_party/licenses/` with their original relative paths. Canonical GPL/LGPL texts were obtained from the SPDX license-list-data repository. Python's supplied license is included when available. The metadata table is informational; the original component license texts prevail.

- Python: https://www.python.org/ ; source: https://github.com/python/cpython
- PyQt5: https://www.riverbankcomputing.com/software/pyqt/ ; source distribution: https://pypi.org/project/PyQt5/#files
- Qt: https://www.qt.io/licensing/ ; source archives: https://download.qt.io/archive/qt/
- pywin32: https://github.com/mhammond/pywin32
- deep-translator: https://github.com/nidhaloff/deep-translator
- requests: https://github.com/psf/requests
- PyInstaller: https://github.com/pyinstaller/pyinstaller

A public binary release must provide the corresponding project source and satisfy the source/notice requirements of the exact bundled components. No public binary release is created by the current preparation workflow.
