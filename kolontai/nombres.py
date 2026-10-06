# Kolontái — lectura de nombres de archivo
# SPDX-License-Identifier: GPL-3.0-or-later
"""Interpreta nombres con el estándar PREFIJO_NÚMERO_dd.mm.aaaa_TERCERO."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

PREFIJOS = {
    "CE": "Comprobante de egreso",
    "FV": "Factura electrónica de venta",
    "DSE": "Documento soporte electrónico",
    "PAGO": "Comprobante de pago",
    "ANEXO": "Anexo",
    "NM": "Planilla de nómina",
    "PAGONM": "Pago de nómina",
}

EXTENSIONES = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}

# Acepta dd.mm.aaaa y, con aviso, dd-mm-aaaa o dd/mm/aaaa
_FECHA = re.compile(r"^(\d{1,2})([.\-/])(\d{1,2})\2(\d{4})$")


@dataclass
class Documento:
    ruta: Path
    prefijo: str = ""
    numero: str = ""
    fecha: date | None = None
    tercero: str = ""
    avisos: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def valido(self) -> bool:
        return not self.error

    @property
    def clave(self) -> str:
        """Tercero normalizado, para comparar nombres escritos distinto."""
        return normalizar(self.tercero)

    @property
    def nombre(self) -> str:
        return self.ruta.name


def normalizar(texto: str) -> str:
    """'Ferretería El Tornillo S.A.S.' -> 'ferreteria el tornillo sas'"""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower().replace(".", "")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", texto).split())


def leer(ruta: Path) -> Documento:
    """Convierte un nombre de archivo en un Documento (válido o con error)."""
    doc = Documento(ruta=ruta)
    # maxsplit=3: el tercero puede traer guiones bajos y queda entero
    partes = [p.strip() for p in ruta.stem.split("_", 3)]
    if len(partes) != 4 or not all(partes):
        doc.error = "No sigue el estándar PREFIJO_NÚMERO_FECHA_TERCERO"
        return doc
    prefijo, numero, fecha, tercero = partes

    # Comparación exacta: así PAGONM nunca se confunde con PAGO
    if prefijo.upper() not in PREFIJOS:
        doc.error = f"Prefijo desconocido: {prefijo}"
        return doc
    if prefijo != prefijo.upper():
        doc.avisos.append(f"Prefijo en minúsculas ({prefijo})")
    doc.prefijo = prefijo.upper()
    doc.numero = numero

    m = _FECHA.match(fecha)
    if not m:
        doc.error = f"Fecha ilegible: {fecha}"
        return doc
    dia, separador, mes, anio = m.groups()
    try:
        doc.fecha = date(int(anio), int(mes), int(dia))
    except ValueError:
        doc.error = f"Fecha imposible: {fecha}"
        return doc
    if separador != ".":
        doc.avisos.append(f"Fecha con '{separador}' en vez de '.'")

    if "_" in tercero:
        doc.avisos.append("Guion bajo dentro del nombre del tercero")
    doc.tercero = " ".join(tercero.replace("_", " ").split())
    return doc


def escanear(carpeta: Path) -> tuple[list[Documento], list[Path]]:
    """Lee la carpeta (sin subcarpetas). Devuelve (documentos, ignorados)."""
    documentos: list[Documento] = []
    ignorados: list[Path] = []
    for ruta in sorted(carpeta.iterdir(), key=lambda r: r.name.lower()):
        if not ruta.is_file():
            continue
        if ruta.suffix.lower() in EXTENSIONES:
            documentos.append(leer(ruta))
        else:
            ignorados.append(ruta)
    return documentos, ignorados
