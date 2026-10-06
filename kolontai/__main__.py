# Kolontái — interfaz de consola
# SPDX-License-Identifier: GPL-3.0-or-later
"""Uso: python -m kolontai CARPETA [--generar]"""

import argparse
import sys
from pathlib import Path

from . import __version__
from .agrupador import Resultado, analizar
from .unir import generar


def imprimir_vista_previa(r: Resultado) -> None:
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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kolontai", description="Une los soportes contables de cada tercero en un solo PDF.")
    p.add_argument("carpeta", type=Path, help="carpeta con los documentos del mes")
    p.add_argument("--generar", action="store_true", help="crear los PDF (sin esto solo muestra la vista previa)")
    p.add_argument("--version", action="version", version=f"Kolontái {__version__}")
    args = p.parse_args(argv)

    if not args.carpeta.is_dir():
        print(f"No existe la carpeta: {args.carpeta}")
        return 2

    r = analizar(args.carpeta)
    print(f"Kolontái {__version__} · {args.carpeta.resolve()}")
    imprimir_vista_previa(r)
    if not args.generar:
        print("\n(Vista previa. Agregue --generar para crear los PDF.)")
        return 0

    print("\nGenerando...")
    salidas, reporte = generar(r, args.carpeta, lambda i, t, n: print(f"  [{i}/{t}] {n}"))
    errores = [s for s in salidas if s.error]
    for s in errores:
        print(f"  ✘ {s.grupo.nombre_salida}: {s.error}")
    print(f"\n{len(salidas) - len(errores)} PDF generados, {len(errores)} con error.")
    print(f"Reporte: {reporte}")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
