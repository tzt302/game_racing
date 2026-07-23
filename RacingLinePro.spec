# -*- mode: python ; coding: utf-8 -*-

datas = [
    ('config.py', '.'),
    # Frozen ``track.track`` lives at ``_MEIPASS/track`` rather than
    # ``_MEIPASS/src/track``, so its adjacent JSON must use the same prefix.
    ('src/track/telemetry_layouts.json', 'track'),
]
binaries = []
hiddenimports = []


a = Analysis(
    ['main.py'],
    # main.py adds ``src`` to sys.path at runtime. PyInstaller also needs the
    # same path during static analysis, otherwise top-level packages such as
    # ``game`` are omitted from the one-file executable.
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'numpy.tests', 'pygame.tests'],
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
    name='RacingLinePro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='packaging/version_info.txt',
)
