#!/usr/bin/env python3
# Kolontái — genera kolontai.ico y kolontai.png a partir de kolontai.svg
# SPDX-License-Identifier: GPL-3.0-or-later
# Requiere: pip install cairosvg  (y en Debian: sudo apt install libcairo2)
import io
from pathlib import Path

import cairosvg
from PIL import Image

RECURSOS = Path(__file__).resolve().parent.parent / "kolontai" / "recursos"
SVG = RECURSOS / "kolontai.svg"
TAMANOS = [256, 128, 64, 48, 32, 24, 16]


def renderizar(tam: int) -> Image.Image:
    png = cairosvg.svg2png(url=str(SVG), output_width=tam, output_height=tam)
    return Image.open(io.BytesIO(png)).convert("RGBA")


# Cada tamaño se dibuja desde el SVG, no se reduce desde el grande: queda más nítido
imagenes = [renderizar(t) for t in TAMANOS]
imagenes[0].save(RECURSOS / "kolontai.ico", format="ICO",
                 sizes=[(t, t) for t in TAMANOS], append_images=imagenes[1:])
renderizar(512).save(RECURSOS / "kolontai.png")
print("Listo:", RECURSOS / "kolontai.ico", RECURSOS / "kolontai.png")
