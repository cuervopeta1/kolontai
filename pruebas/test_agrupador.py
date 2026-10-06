# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path

import pytest

from kolontai.agrupador import agrupar, analizar
from kolontai.nombres import leer


def grupos_de(*nombres):
    return agrupar([leer(Path(n)) for n in nombres])


def test_caso_ideal_y_orden():
    r = grupos_de(
        "ANEXO_1_05.09.2026_Ferreteria.png",
        "PAGO_9_05.09.2026_Ferreteria.jpg",
        "CE_1001_05.09.2026_Ferreteria.pdf",
        "FV_FE1_03.09.2026_Ferreteria.pdf",
    )
    (g,) = r.grupos
    assert [d.prefijo for d in g.documentos] == ["CE", "FV", "PAGO", "ANEXO"]
    assert g.nombre_salida == "CEC_1001_05.09.2026_Ferreteria.pdf"
    assert not g.revisar


def test_tildes_y_mayusculas_no_separan_terceros():
    r = grupos_de("CE_1_08.09.2026_Maria Gomez.pdf", "DSE_2_08.09.2026_MARÍA GÓMEZ.pdf")
    assert len(r.grupos[0].soportes) == 1 and not r.huerfanos


def test_tercero_parecido_se_une_con_aviso():
    r = grupos_de("CE_1_05.09.2026_Ferreteria El Tornillo SAS.pdf",
                  "FV_2_05.09.2026_Ferreteria El Tornilo SAS.pdf")
    assert len(r.grupos[0].soportes) == 1 and r.grupos[0].revisar


def test_dos_egresos_mismo_tercero_por_fecha():
    r = grupos_de(
        "CE_1003_10.09.2026_Ruta.pdf", "CE_1007_24.09.2026_Ruta.pdf",
        "FV_A_09.09.2026_Ruta.pdf", "FV_B_23.09.2026_Ruta.pdf",
        "PAGO_1_10.09.2026_Ruta.jpg", "PAGO_2_24.09.2026_Ruta.jpg",
    )
    primero, segundo = r.grupos
    assert {d.numero for d in primero.soportes} == {"A", "1"}
    assert {d.numero for d in segundo.soportes} == {"B", "2"}
    assert primero.revisar and segundo.revisar  # las facturas no tienen la misma fecha


def test_nomina_con_su_pago():
    r = grupos_de(
        "NM_500_15.09.2026_Septiembre.pdf", "NM_501_30.09.2026_Septiembre.pdf",
        "PAGONM_1_15.09.2026_Septiembre.pdf", "PAGONM_2_30.09.2026_Septiembre.jpg",
    )
    assert [g.nombre_salida[:7] for g in r.grupos] == ["NMC_500", "NMC_501"]
    assert all(len(g.soportes) == 1 and not g.revisar for g in r.grupos)


def test_huerfano_y_pago_no_va_a_nomina():
    r = grupos_de("NM_1_30.09.2026_Septiembre.pdf", "PAGO_9_30.09.2026_Septiembre.jpg")
    assert [d.prefijo for d in r.huerfanos] == ["PAGO"]


def test_numero_de_ce_repetido():
    r = grupos_de("CE_1_01.09.2026_A.pdf", "CE_1_02.09.2026_B.pdf")
    assert any("repetido" in a for g in r.grupos for a in g.avisos)


MUESTRAS = Path(__file__).parent.parent / "muestras" / "septiembre"


@pytest.mark.skipif(not MUESTRAS.is_dir(), reason="no se han generado las muestras")
def test_carpeta_de_muestras():
    r = analizar(MUESTRAS)
    assert len(r.grupos) == 8
    assert [d.nombre for d in r.huerfanos] == ["FV_A3390_15.09.2026_Papeleria Central.pdf"]
    assert len(r.invalidos) == 2 and len(r.ignorados) == 1
