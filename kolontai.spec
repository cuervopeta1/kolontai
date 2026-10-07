# -*- mode: python ; coding: utf-8 -*-
# Kolontái — receta de PyInstaller
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Uso (en Windows):  pyinstaller --noconfirm kolontai.spec
# Resultado:         dist\Kolontai\Kolontai.exe  (carpeta completa, no un solo .exe)

import re
from pathlib import Path


VERSION = re.search(r'__version__ = "([^"]+)"',
                    Path("kolontai/__init__.py").read_text(encoding="utf-8")).group(1)
NUMEROS = tuple(int(x) for x in VERSION.split(".")) + (0,)

# Datos que muestra Windows en Propiedades > Detalles del .exe
# (fuera de Windows no aplican; así la receta también se puede probar en Linux)
try:
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable,
        VarFileInfo, VarStruct, VSVersionInfo,
    )
except ImportError:
    VSVersionInfo = None

version_windows = VSVersionInfo and VSVersionInfo(
    ffi=FixedFileInfo(filevers=NUMEROS, prodvers=NUMEROS),
    kids=[
        StringFileInfo([StringTable("0C0A04B0", [
            StringStruct("CompanyName", "Juan Sebastián Berrío Posada"),
            StringStruct("FileDescription", "Kolontái - organizador de soportes contables"),
            StringStruct("FileVersion", VERSION),
            StringStruct("InternalName", "Kolontai"),
            StringStruct("LegalCopyright", "© 2026 Juan Sebastián Berrío Posada · GPL-3.0-or-later"),
            StringStruct("OriginalFilename", "Kolontai.exe"),
            StringStruct("ProductName", "Kolontái"),
            StringStruct("ProductVersion", VERSION),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x0C0A, 1200])]),
    ],
)

a = Analysis(
    ["kolontai_inicio.py"],
    datas=[("kolontai/recursos", "kolontai/recursos"), ("LICENSE", ".")],
    excludes=["tkinter", "pytest", "cairosvg", "numpy"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Kolontai",
    icon="kolontai/recursos/kolontai.ico",
    version=version_windows,
    console=False,  # sin ventana negra de consola
    upx=False,      # UPX dispara falsos positivos en los antivirus
)
coll = COLLECT(exe, a.binaries, a.datas, name="Kolontai", upx=False)
