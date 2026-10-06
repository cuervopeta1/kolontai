# Kolontái — vista previa por consola
# SPDX-License-Identifier: GPL-3.0-or-later
"""Uso: python -m kolontai CARPETA"""

import sys
from pathlib import Path

from . import __version__
from .agrupador import analizar


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Uso: python -m kolontai CARPETA")
        return 2
    carpeta = Path(argv[0])
    if not carpeta.is_dir():
        print(f"No existe la carpeta: {carpeta}")
        return 2

    r = analizar(carpeta)
    print(f"Kolontái {__version__} · vista previa de {carpeta.resolve()}")

    for g in r.grupos:
        print(f"\n{'⚠' if g.revisar else '✔'} {g.nombre_salida}")
        for d in g.documentos:
            print(f"     {d.nombre}")
            for a in d.avisos:
                print(f"        · {a}")
        for a in g.avisos:
            print(f"   ⚠ {a}")

    if r.huerfanos:
        print("\nSOPORTES SIN COMPROBANTE")
        for d in r.huerfanos:
            print(f"   {d.nombre}")
    if r.invalidos:
        print("\nNOMBRES FUERA DEL ESTÁNDAR")
        for d in r.invalidos:
            print(f"   {d.nombre}  →  {d.error}")
    if r.ignorados:
        print("\nIGNORADOS (formato no soportado)")
        for p in r.ignorados:
            print(f"   {p.name}")

    revisar = sum(g.revisar for g in r.grupos)
    print(
        f"\nResumen: {len(r.grupos)} grupos ({revisar} para revisar), "
        f"{len(r.huerfanos)} huérfanos, {len(r.invalidos)} fuera del estándar, "
        f"{len(r.ignorados)} ignorados."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
