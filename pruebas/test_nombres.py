# SPDX-License-Identifier: GPL-3.0-or-later
from datetime import date
from pathlib import Path

from kolontai.nombres import leer, normalizar


def test_nombre_estandar():
    d = leer(Path("CE_1001_05.09.2026_Ferreteria El Tornillo SAS.pdf"))
    assert d.valido and not d.avisos
    assert (d.prefijo, d.numero, d.fecha, d.tercero) == (
        "CE", "1001", date(2026, 9, 5), "Ferreteria El Tornillo SAS")


def test_pagonm_no_se_confunde_con_pago():
    assert leer(Path("PAGONM_77001_30.09.2026_Septiembre.jpg")).prefijo == "PAGONM"
    assert leer(Path("PAGO_88213_05.09.2026_X.jpg")).prefijo == "PAGO"


def test_guion_bajo_en_tercero():
    d = leer(Path("CE_1008_26.09.2026_Lavanderia_La Espuma.pdf"))
    assert d.valido and d.tercero == "Lavanderia La Espuma" and d.avisos


def test_minusculas_y_guiones_se_aceptan_con_aviso():
    d = leer(Path("ce_1006_12-09-2026_Aseo Total SAS.pdf"))
    assert d.valido and d.prefijo == "CE" and len(d.avisos) == 2


def test_fecha_imposible():
    assert "imposible" in leer(Path("CE_1005_31.09.2026_Servicios Web.pdf")).error


def test_sin_estandar_y_prefijo_desconocido():
    assert not leer(Path("factura tornillo septiembre.pdf")).valido
    assert "desconocido" in leer(Path("RC_1_01.09.2026_X.pdf")).error


def test_normalizar():
    assert normalizar("Ferretería El Tornillo S.A.S.") == "ferreteria el tornillo sas"
    assert normalizar("MARÍA  fernanda GÓMEZ") == "maria fernanda gomez"
