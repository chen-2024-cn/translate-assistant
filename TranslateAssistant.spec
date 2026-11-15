# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['deep_translator', 'win32com', 'win32com.client', 'win32api', 'win32con', 'win32gui', 'win32process', 'win32console', 'win32event', 'winerror', 'pythoncom', 'pywintypes', 'requests', 're', 'signal']
hiddenimports += collect_submodules('deep_translator')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('config.py', '.'),
           ('LICENSE', '.'), ('THIRD_PARTY_NOTICES.md', '.'), ('third_party', 'third_party')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TranslateAssistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
