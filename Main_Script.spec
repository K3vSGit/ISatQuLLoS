# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)


block_cipher = None

hiddenimports = [
    "ICONS_rc",
    "ISatQuLLoS",
    "Logic",
    "PyQt5",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    "PyQt5.QtWebEngineCore",
    "PyQt5.QtWebEngineWidgets",
    "matplotlib",
    "matplotlib.backends.backend_qt5agg",
    "mpl_toolkits.mplot3d",
    "numpy",
    "plotly",
    "plotly.graph_objects",
    "plotly.offline",
    "scipy",
    "scipy.integrate",
    "scipy.linalg",
    "scipy.optimize",
    "scipy.sparse",
    "scipy.special",
    "scipy.special._basic",
    "scipy.special._ufuncs",
    "scipy.special._ufuncs_cxx",
    "scipy.integrate._quadrature",
    "Ui_Design",
]

hiddenimports += collect_submodules("PyQt5.QtWebEngineCore")
hiddenimports += collect_submodules("PyQt5.QtWebEngineWidgets")

datas = []
datas += collect_data_files("plotly")
datas += collect_data_files("PyQt5", includes=[
    "Qt5/resources/*",
    "Qt5/translations/*",
    "Qt5/bin/QtWebEngineProcess.exe",
])

binaries = []
binaries += collect_dynamic_libs("PyQt5")
binaries += collect_dynamic_libs("scipy")


a = Analysis(
    ["Main_Script.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "scipy.integrate.tests",
        "scipy.special.tests",
        "pytest",
        "hypothesis",
        "mpmath",
        "sympy",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ISatQuLLoS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ISatQuLLoS",
)
