#!/usr/bin/env python3
# Kolontái - generador de documentos contables ficticios para pruebas.
# Licencia: GPL-3.0-or-later
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DESTINO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("muestras/septiembre")
A4 = (827, 1169)        # A4 a 100 dpi
TIRILLA = (600, 900)    # comprobantes tipo foto o pantallazo

TIPOS = {
    "CE":     ("Comprobante de egreso",         (40, 90, 160)),
    "FV":     ("Factura electrónica de venta",  (30, 130, 70)),
    "DSE":    ("Documento soporte electrónico", (20, 120, 120)),
    "PAGO":   ("Comprobante de pago",           (190, 110, 20)),
    "ANEXO":  ("Anexo",                         (110, 110, 110)),
    "NM":     ("Planilla de nómina",            (140, 40, 120)),
    "PAGONM": ("Pago de nómina",                (170, 50, 50)),
}

# (nombre del archivo, páginas). Los casos raros son intencionales.
ARCHIVOS = [
    # 1. Caso ideal: un CE con factura, pago y anexo
    ("CE_1001_05.09.2026_Ferreteria El Tornillo SAS.pdf", 1),
    ("FV_FE4521_03.09.2026_Ferreteria El Tornillo SAS.pdf", 2),
    ("PAGO_88213_05.09.2026_Ferreteria El Tornillo SAS.jpg", 1),
    ("ANEXO_1_05.09.2026_Ferreteria El Tornillo SAS.png", 1),
    # 2. Documento soporte; el tercero varía en tildes y mayúsculas
    ("CE_1002_08.09.2026_Maria Fernanda Gomez.pdf", 1),
    ("DSE_DS120_08.09.2026_María Fernanda Gómez.pdf", 1),
    ("PAGO_88290_08.09.2026_MARIA FERNANDA GOMEZ.jpeg", 1),
    # 3. Mismo tercero con dos egresos en el mes (caso ambiguo)
    ("CE_1003_10.09.2026_Transportes La Ruta SAS.pdf", 1),
    ("FV_TR880_09.09.2026_Transportes La Ruta SAS.pdf", 1),
    ("PAGO_88301_10.09.2026_Transportes La Ruta SAS.jpg", 1),
    ("ANEXO_2_10.09.2026_Transportes La Ruta SAS.tif", 1),
    ("CE_1007_24.09.2026_Transportes La Ruta SAS.pdf", 1),
    ("FV_TR901_23.09.2026_Transportes La Ruta SAS.pdf", 3),
    ("PAGO_88477_24.09.2026_Transportes La Ruta SAS.png", 1),
    ("ANEXO_3_24.09.2026_Transportes La Ruta SAS.PDF", 1),
    # 4. Nómina: quincena y fin de mes con el mismo mes en el nombre
    ("NM_500_15.09.2026_Septiembre.pdf", 2),
    ("PAGONM_76990_15.09.2026_Septiembre.pdf", 1),
    ("NM_501_30.09.2026_Septiembre.pdf", 2),
    ("PAGONM_77001_30.09.2026_Septiembre.jpg", 1),
    # 5. Huérfanos: soportes sin comprobante de egreso
    ("FV_A3390_15.09.2026_Papeleria Central.pdf", 1),
    ("PAGO_88350_18.09.2026_Aseo Total SAS.jpg", 1),
    # 6. Nombres que no cumplen el estándar
    ("factura tornillo septiembre.pdf", 1),
    ("CE_1005_31.09.2026_Servicios Web Ltda.pdf", 1),    # fecha imposible
    ("ce_1006_12-09-2026_Aseo Total SAS.pdf", 1),        # minúsculas y guiones
    ("CE_1008_26.09.2026_Lavanderia_La Espuma.pdf", 1),  # guion bajo en el tercero
    # 7. Basura que deja Windows
    ("desktop.ini", 0),
]


def fuente(tam):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", tam)
    except OSError:
        return ImageFont.load_default(size=tam)


def pagina(nombre, n, total, tam):
    prefijo = nombre.split("_")[0].upper()
    titulo, color = TIPOS.get(prefijo, ("Documento sin estándar", (90, 90, 90)))
    img = Image.new("RGB", tam, "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, tam[0], 110], fill=color)
    d.text((40, 32), titulo.upper(), font=fuente(34), fill="white")
    y = 160
    for parte in Path(nombre).stem.split("_"):
        d.text((40, y), parte, font=fuente(30), fill="black")
        y += 50
    d.text((40, tam[1] - 70), f"Página {n} de {total} · PRUEBA KOLONTÁI",
           font=fuente(20), fill=(120, 120, 120))
    return img


def guardar(nombre, paginas):
    ruta = DESTINO / nombre
    ext = ruta.suffix.lower()
    if ext == ".pdf":
        hojas = [pagina(nombre, i + 1, paginas, A4) for i in range(paginas)]
        hojas[0].save(ruta, "PDF", resolution=100, save_all=True, append_images=hojas[1:])
    elif ext in (".jpg", ".jpeg"):
        pagina(nombre, 1, 1, TIRILLA).save(ruta, "JPEG", quality=85)
    elif ext == ".png":
        # RGBA a propósito: así quedan los pantallazos y obliga a manejar el canal alfa
        pagina(nombre, 1, 1, TIRILLA).convert("RGBA").save(ruta, "PNG")
    elif ext in (".tif", ".tiff"):
        pagina(nombre, 1, 1, A4).save(ruta, "TIFF", compression="tiff_lzw")
    else:
        ruta.write_text("[.ShellClassInfo]\nIconResource=C:\\Windows\\System32\\imageres.dll,-3\n")


if __name__ == "__main__":
    DESTINO.mkdir(parents=True, exist_ok=True)
    for nombre, paginas in ARCHIVOS:
        guardar(nombre, paginas)
        print("✔", nombre)
    print(f"\n{len(ARCHIVOS)} archivos generados en {DESTINO.resolve()}")
