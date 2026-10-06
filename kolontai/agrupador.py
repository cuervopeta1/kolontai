# Kolontái — agrupación de soportes por comprobante
# SPDX-License-Identifier: GPL-3.0-or-later
"""Arma los grupos: cada CE (o NM) con sus soportes, en orden."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz, process

from .nombres import Documento, escanear

# Documento ancla -> prefijo del archivo de salida y soportes en orden de unión
REGLAS = {
    "CE": {"salida": "CEC", "soportes": ["FV", "DSE", "PAGO", "ANEXO"]},
    "NM": {"salida": "NMC", "soportes": ["PAGONM"]},
}
ANCLA_DE = {s: ancla for ancla, r in REGLAS.items() for s in r["soportes"]}

UMBRAL_PARECIDO = 90  # % mínimo para aceptar un tercero escrito un poco distinto
_PROHIBIDOS_WINDOWS = re.compile(r'[<>:"/\\|?*]')


@dataclass
class Grupo:
    ancla: Documento
    soportes: list[Documento] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def documentos(self) -> list[Documento]:
        """Ancla primero; luego los soportes en el orden de REGLAS."""
        orden = REGLAS[self.ancla.prefijo]["soportes"]
        return [self.ancla] + sorted(
            self.soportes, key=lambda d: (orden.index(d.prefijo), d.fecha, d.numero)
        )

    @property
    def nombre_salida(self) -> str:
        a = self.ancla
        prefijo = REGLAS[a.prefijo]["salida"]
        tercero = _PROHIBIDOS_WINDOWS.sub("", a.tercero).strip()
        return f"{prefijo}_{a.numero}_{a.fecha:%d.%m.%Y}_{tercero}.pdf"

    @property
    def revisar(self) -> bool:
        return bool(self.avisos) or any(d.avisos for d in self.documentos)


@dataclass
class Resultado:
    grupos: list[Grupo]
    huerfanos: list[Documento]
    invalidos: list[Documento]
    ignorados: list[Path]


def agrupar(documentos: list[Documento], ignorados: list[Path] | None = None) -> Resultado:
    invalidos = [d for d in documentos if not d.valido]
    validos = [d for d in documentos if d.valido]
    grupos = [Grupo(d) for d in validos if d.prefijo in REGLAS]
    huerfanos: list[Documento] = []

    vistos: dict[tuple[str, str], Documento] = {}
    for g in grupos:
        llave = (g.ancla.prefijo, g.ancla.numero)
        if llave in vistos:
            g.avisos.append(f"Número repetido: también aparece en {vistos[llave].nombre}")
        else:
            vistos[llave] = g.ancla

    for doc in validos:
        if doc.prefijo in REGLAS:
            continue
        candidatos = [g for g in grupos if g.ancla.prefijo == ANCLA_DE[doc.prefijo]]
        elegido = _elegir(doc, candidatos)
        if elegido is None:
            huerfanos.append(doc)
        else:
            elegido.soportes.append(doc)

    for g in grupos:
        if not g.soportes:
            g.avisos.append("Sin soportes: solo contiene el comprobante")

    grupos.sort(key=lambda g: (list(REGLAS).index(g.ancla.prefijo), g.ancla.fecha, g.ancla.numero))
    return Resultado(grupos, huerfanos, invalidos, ignorados or [])


def _elegir(doc: Documento, candidatos: list[Grupo]) -> Grupo | None:
    """Decide a qué grupo va un soporte. Deja avisos cuando la decisión no es segura."""
    mismos = [g for g in candidatos if g.ancla.clave == doc.clave]
    aviso_nombre = ""
    if not mismos:
        claves = sorted({g.ancla.clave for g in candidatos})
        parecido = process.extractOne(
            doc.clave, claves, scorer=fuzz.token_sort_ratio, score_cutoff=UMBRAL_PARECIDO
        )
        if parecido is None:
            return None
        mismos = [g for g in candidatos if g.ancla.clave == parecido[0]]
        aviso_nombre = f"{doc.nombre}: el tercero se parece pero no es idéntico ({parecido[1]:.0f} %)"

    if len(mismos) == 1:
        elegido = mismos[0]
    else:
        # Varios comprobantes del mismo tercero: gana el de fecha más cercana
        def distancia(g: Grupo) -> int:
            return abs((g.ancla.fecha - doc.fecha).days)

        mismos.sort(key=lambda g: (distancia(g), g.ancla.fecha))
        elegido = mismos[0]
        mismo_dia = [g for g in mismos if distancia(g) == 0]
        if len(mismo_dia) != 1:  # sin coincidencia exacta de fecha, o empate
            elegido.avisos.append(
                f"{doc.nombre}: asignado por fecha más cercana "
                f"entre {len(mismos)} comprobantes del mismo tercero"
            )

    if aviso_nombre:
        elegido.avisos.append(aviso_nombre)
    return elegido


def analizar(carpeta: Path) -> Resultado:
    return agrupar(*escanear(carpeta))
