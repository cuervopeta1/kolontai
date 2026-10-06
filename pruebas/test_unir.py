# SPDX-License-Identifier: GPL-3.0-or-later
from PIL import Image
from pypdf import PdfReader, PdfWriter

from kolontai.agrupador import analizar
from kolontai.unir import generar


def pdf(ruta, paginas=1):
    hojas = [Image.new("RGB", (200, 280), "white") for _ in range(paginas)]
    hojas[0].save(ruta, "PDF", save_all=True, append_images=hojas[1:])


def test_une_pdf_e_imagenes_en_orden_con_marcadores(tmp_path):
    pdf(tmp_path / "CE_1_05.09.2026_Ferreteria.pdf")
    pdf(tmp_path / "FV_2_05.09.2026_Ferreteria.pdf", paginas=2)
    Image.new("RGB", (300, 500), "white").save(tmp_path / "PAGO_3_05.09.2026_Ferreteria.jpg")
    Image.new("RGBA", (300, 500), (0, 0, 0, 0)).save(tmp_path / "ANEXO_4_05.09.2026_Ferreteria.png")

    salidas, reporte = generar(analizar(tmp_path), tmp_path)
    (s,) = salidas
    assert not s.error and s.paginas == 5
    lector = PdfReader(s.ruta)
    assert [o.title[:2] for o in lector.outline] == ["CE", "FV", "PA", "AN"]
    assert reporte.exists()


def test_no_sobrescribe(tmp_path):
    pdf(tmp_path / "CE_1_05.09.2026_X.pdf")
    generar(analizar(tmp_path), tmp_path)
    salidas, _ = generar(analizar(tmp_path), tmp_path)
    assert salidas[0].ruta.name == "CEC_1_05.09.2026_X (2).pdf"


def test_pdf_con_clave_de_propietario_se_abre(tmp_path):
    pdf(tmp_path / "base.pdf")
    w = PdfWriter(clone_from=tmp_path / "base.pdf")
    w.encrypt(user_password="", owner_password="dian")
    w.write(tmp_path / "CE_1_05.09.2026_X.pdf")
    (tmp_path / "base.pdf").unlink()
    salidas, _ = generar(analizar(tmp_path), tmp_path)
    assert not salidas[0].error


def test_archivo_danado_no_detiene_los_demas(tmp_path):
    (tmp_path / "CE_1_05.09.2026_A.pdf").write_bytes(b"esto no es un pdf")
    pdf(tmp_path / "CE_2_06.09.2026_B.pdf")
    salidas, _ = generar(analizar(tmp_path), tmp_path)
    assert salidas[0].error and not salidas[1].error
