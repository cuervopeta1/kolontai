# Kolontái — unión de documentos en un solo PDF
# SPDX-License-Identifier: GPL-3.0-or-later
"""Convierte imágenes a PDF y une los documentos de cada grupo."""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import img2pdf
from PIL import Image
from pypdf import PdfReader, PdfWriter

from .agrupador import Grupo, Resultado
from .nombres import Documento

CARPETA_SALIDA = "Kolontai_salida"

# img2pdf avisa por consola cada transparencia que procesa; no nos interesa
logging.getLogger("img2pdf").setLevel(logging.ERROR)

# Las imágenes se ubican en una hoja A4, girada si la imagen es horizontal
_A4 = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))
_DISENO_A4 = img2pdf.get_layout_fun(_A4, fit=img2pdf.FitMode.into, auto_orient=True)


@dataclass
class Salida:
    grupo: Grupo
    ruta: Path | None = None
    paginas: int = 0
    error: str = ""


def imagen_a_pdf(ruta: Path) -> bytes:
    """Imagen -> PDF sin recomprimir cuando se puede (JPG pasa tal cual)."""
    try:
        return img2pdf.convert(str(ruta), layout_fun=_DISENO_A4,
                               rotation=img2pdf.Rotation.ifvalid)
    except Exception:
        # Transparencias, paletas o formatos raros: aplanar sobre fondo blanco
        with Image.open(ruta) as img:
            img = img.convert("RGBA")
            fondo = Image.new("RGB", img.size, "white")
            fondo.paste(img, mask=img.getchannel("A"))
            buffer = io.BytesIO()
            fondo.save(buffer, "PNG")
        return img2pdf.convert(buffer.getvalue(), layout_fun=_DISENO_A4)


def _lector(doc: Documento) -> PdfReader:
    if doc.ruta.suffix.lower() != ".pdf":
        return PdfReader(io.BytesIO(imagen_a_pdf(doc.ruta)))
    lector = PdfReader(doc.ruta)
    if lector.is_encrypted and not lector.decrypt(""):
        raise ValueError(f"{doc.nombre} está protegido con contraseña")
    return lector


def _ruta_libre(ruta: Path) -> Path:
    """Nunca sobrescribe: si existe, agrega (2), (3)..."""
    n = 2
    candidata = ruta
    while candidata.exists():
        candidata = ruta.with_name(f"{ruta.stem} ({n}){ruta.suffix}")
        n += 1
    return candidata


def unir_grupo(grupo: Grupo, destino: Path) -> Salida:
    salida = Salida(grupo)
    try:
        escritor = PdfWriter()
        for doc in grupo.documentos:
            # Cada documento queda como marcador en el panel del lector de PDF
            escritor.append(_lector(doc), outline_item=doc.ruta.stem)
        escritor.page_mode = "/UseOutlines"
        ruta = _ruta_libre(destino / grupo.nombre_salida)
        with open(ruta, "wb") as f:
            escritor.write(f)
        salida.ruta, salida.paginas = ruta, len(escritor.pages)
    except Exception as e:  # un grupo dañado no detiene los demás
        salida.error = str(e) or e.__class__.__name__
    return salida


def generar(
    resultado: Resultado,
    carpeta: Path,
    progreso: Callable[[int, int, str], None] | None = None,
) -> tuple[list[Salida], Path]:
    """Une todos los grupos en <carpeta>/Kolontai_salida y deja un reporte CSV."""
    destino = carpeta / CARPETA_SALIDA
    destino.mkdir(exist_ok=True)
    salidas = []
    total = len(resultado.grupos)
    for i, grupo in enumerate(resultado.grupos, 1):
        if progreso:
            progreso(i, total, grupo.nombre_salida)
        salidas.append(unir_grupo(grupo, destino))
    reporte = escribir_reporte(salidas, resultado, destino)
    return salidas, reporte


def escribir_reporte(salidas: list[Salida], resultado: Resultado, destino: Path) -> Path:
    """CSV con ';' y BOM para que Excel en español lo abra bien."""
    ruta = destino / f"reporte_{datetime.now():%Y-%m-%d_%H%M%S}.csv"
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["estado", "archivo_generado", "paginas", "documentos", "observaciones"])
        for s in salidas:
            observaciones = s.grupo.avisos + [
                f"{d.nombre}: {a}" for d in s.grupo.documentos for a in d.avisos
            ]
            if s.error:
                estado = "ERROR"
                observaciones.insert(0, s.error)
            else:
                estado = "REVISAR" if s.grupo.revisar else "OK"
            w.writerow([
                estado,
                s.ruta.name if s.ruta else s.grupo.nombre_salida,
                s.paginas,
                " | ".join(d.nombre for d in s.grupo.documentos),
                " | ".join(observaciones),
            ])
        for d in resultado.huerfanos:
            w.writerow(["SIN COMPROBANTE", "", "", d.nombre, ""])
        for d in resultado.invalidos:
            w.writerow(["FUERA DEL ESTÁNDAR", "", "", d.nombre, d.error])
        for p in resultado.ignorados:
            w.writerow(["IGNORADO", "", "", p.name, "Formato no soportado"])
    return ruta
