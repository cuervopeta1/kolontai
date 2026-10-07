# Kolontái

Programa de escritorio para Windows que organiza los soportes contables de un mes. Lee una carpeta con comprobantes de egreso, facturas, documentos soporte, comprobantes de pago, anexos y nómina, y une en un solo PDF los documentos de cada tercero.

## Nombres que reconoce

| Prefijo | Documento | Ejemplo |
|---|---|---|
| CE | Comprobante de egreso | `CE_1001_05.09.2026_Ferreteria El Tornillo SAS.pdf` |
| FV | Factura electrónica | `FV_FE4521_03.09.2026_Ferreteria El Tornillo SAS.pdf` |
| DSE | Documento soporte electrónico | `DSE_DS120_08.09.2026_Maria Fernanda Gomez.pdf` |
| PAGO | Comprobante de pago | `PAGO_88213_05.09.2026_Ferreteria El Tornillo SAS.jpg` |
| ANEXO | Anexo | `ANEXO_1_05.09.2026_Ferreteria El Tornillo SAS.png` |
| NM | Planilla de nómina | `NM_501_30.09.2026_Septiembre.pdf` |
| PAGONM | Pago de nómina | `PAGONM_77001_30.09.2026_Septiembre.jpg` |

Cada CE se une con las FV, DSE, PAGO y ANEXO del mismo tercero y genera `CEC_<número del CE>_<fecha>_<tercero>.pdf`. Cada NM se une con su PAGONM y genera `NMC_...pdf`. Acepta PDF, JPG, PNG, TIFF, BMP y WEBP.

Los archivos originales no se modifican. Los PDF se guardan en la subcarpeta `Kolontai_salida`, junto con un reporte CSV que indica qué se unió, qué quedó por revisar y qué no cumple el estándar.

## Uso

1. Abra Kolontái y pulse **Elegir carpeta…**.
2. Revise los grupos. Los amarillos tienen observaciones. Un soporte se puede arrastrar de un grupo a otro, o desde la pestaña **Sin comprobante**.
3. Pulse **Generar PDF**.

## Desarrollo (Debian / GNU/Linux)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python herramientas/generar_muestras.py muestras/septiembre   # datos de prueba
python -m pytest -q pruebas
python -m kolontai                                  # ventana
python -m kolontai muestras/septiembre --generar    # consola
```

## Construir para Windows

**Con GitHub Actions** (no requiere un Windows): suba el repositorio a GitHub y, en la pestaña *Actions*, ejecute **Construir para Windows**. También se ejecuta solo al publicar una etiqueta (`git tag v0.3.0 && git push --tags`). Produce el instalador y una versión portable en zip.

**En un Windows con Python 3.12:** haga doble clic en `empaquetar.bat`. Deja el programa en `dist\Kolontai\Kolontai.exe` y, si está instalado [Inno Setup](https://jrsoftware.org/isinfo.php), el instalador en `instalador\salida\`.

El instalador funciona sin permisos de administrador.

## Licencia

Copyright © 2026 Juan Sebastián Berrío Posada.

Kolontái es software libre bajo la [Licencia Pública General GNU, versión 3 o posterior](LICENSE).

El nombre y el logo rinden homenaje a Alexandra Kolontái (1872-1952).
