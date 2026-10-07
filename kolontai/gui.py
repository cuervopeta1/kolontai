# Kolontái — interfaz gráfica
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ventana principal de Kolontái (PySide6)."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QMimeData, QObject, QSettings, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import (QBrush, QColor, QDesktopServices, QDrag, QFont, QIcon,
                           QKeySequence, QPixmap)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QProgressBar, QPushButton, QSplitter, QStyle, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from . import __version__
from .agrupador import REGLAS, Grupo, Resultado, analizar, compatibles, mover
from .nombres import Documento
from .unir import CARPETA_SALIDA, generar

RECURSOS = Path(__file__).resolve().parent / "recursos"
MIME = "application/x-kolontai-documento"
ROL = Qt.ItemDataRole.UserRole

# Colores de estado. El texto va siempre oscuro para que se lea también en modo oscuro.
COLOR_REVISAR = QColor("#fdecb3")
COLOR_REVISADO = QColor("#dcefd8")
COLOR_TEXTO = QColor("#1f1f1f")


def abrir(ruta: Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta)))


def arrastrar(origen: QWidget, doc: Documento) -> None:
    datos = QMimeData()
    datos.setData(MIME, str(doc.ruta).encode("utf-8"))
    datos.setText(doc.nombre)
    drag = QDrag(origen)
    drag.setMimeData(datos)
    drag.exec(Qt.DropAction.MoveAction)


def ruta_soltada(evento) -> str | None:
    datos = evento.mimeData()
    if not datos.hasFormat(MIME):
        return None
    return bytes(datos.data(MIME)).decode("utf-8")


class ArbolGrupos(QTreeWidget):
    """Grupos y sus documentos. Acepta soportes arrastrados sobre un grupo."""

    soltado = Signal(str, object)  # ruta del documento, Grupo destino

    def __init__(self) -> None:
        super().__init__()
        self.setHeaderLabels(["Archivo", "Fecha", "Observaciones"])
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setUniformRowHeights(True)
        cabecera = self.header()
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        cabecera.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setStretchLastSection(True)
        self.setColumnWidth(0, 430)

    def grupo_en(self, punto) -> Grupo | None:
        item = self.itemAt(punto)
        if item is None:
            return None
        if item.parent() is not None:
            item = item.parent()
        return item.data(0, ROL)

    def startDrag(self, acciones) -> None:  # noqa: N802 (nombre de Qt)
        item = self.currentItem()
        doc = item.data(0, ROL) if item else None
        if isinstance(doc, Documento) and doc.prefijo not in REGLAS:
            arrastrar(self, doc)

    def dragEnterEvent(self, e) -> None:  # noqa: N802
        e.acceptProposedAction() if ruta_soltada(e) else e.ignore()

    def dragMoveEvent(self, e) -> None:  # noqa: N802
        if ruta_soltada(e) and self.grupo_en(e.position().toPoint()):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e) -> None:  # noqa: N802
        ruta = ruta_soltada(e)
        grupo = self.grupo_en(e.position().toPoint())
        if ruta and grupo:
            e.acceptProposedAction()
            self.soltado.emit(ruta, grupo)
        else:
            e.ignore()


class ListaSinComprobante(QListWidget):
    """Soportes sin grupo. Se puede arrastrar desde y hacia aquí."""

    soltado = Signal(str, object)  # ruta del documento, None

    def __init__(self) -> None:
        super().__init__()
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)

    def startDrag(self, acciones) -> None:  # noqa: N802
        item = self.currentItem()
        if item:
            arrastrar(self, item.data(ROL))

    def dragEnterEvent(self, e) -> None:  # noqa: N802
        e.acceptProposedAction() if ruta_soltada(e) else e.ignore()

    def dragMoveEvent(self, e) -> None:  # noqa: N802
        e.acceptProposedAction() if ruta_soltada(e) else e.ignore()

    def dropEvent(self, e) -> None:  # noqa: N802
        ruta = ruta_soltada(e)
        if ruta:
            e.acceptProposedAction()
            self.soltado.emit(ruta, None)
        else:
            e.ignore()


class Trabajador(QObject):
    """Genera los PDF en otro hilo para que la ventana no se congele."""

    progreso = Signal(int, int, str)
    terminado = Signal(object, object)  # salidas, ruta del reporte
    fallo = Signal(str)

    def __init__(self, resultado: Resultado, carpeta: Path, grupos: list[Grupo]) -> None:
        super().__init__()
        self.resultado, self.carpeta, self.grupos = resultado, carpeta, grupos

    def run(self) -> None:
        try:
            salidas, reporte = generar(self.resultado, self.carpeta, self.progreso.emit, self.grupos)
            self.terminado.emit(salidas, reporte)
        except Exception as e:  # p. ej. sin permiso de escritura en la carpeta
            self.fallo.emit(str(e) or e.__class__.__name__)


class Ventana(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Kolontái")
        self.resize(1240, 740)
        self.ajustes = QSettings("Kolontai", "Kolontai")
        self.carpeta: Path | None = None
        self.resultado: Resultado | None = None
        self.excluidos: set[int] = set()  # id() de los grupos desmarcados
        self.hilo: QThread | None = None
        self.trabajador: Trabajador | None = None
        self._armar()
        self._mostrar_vacio()

    # ---------- construcción ----------

    def _armar(self) -> None:
        estilo = self.style()
        ayuda = self.menuBar().addMenu("Ayuda")
        ayuda.addAction("Acerca de Kolontái", self.acerca_de)

        self.btn_carpeta = QPushButton(estilo.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon),
                                       "Elegir carpeta…")
        self.btn_carpeta.setShortcut(QKeySequence.StandardKey.Open)
        self.campo_ruta = QLineEdit()
        self.campo_ruta.setReadOnly(True)
        self.campo_ruta.setPlaceholderText("Elija la carpeta del mes, por ejemplo «Septiembre»")
        self.btn_releer = QPushButton(estilo.standardIcon(QStyle.StandardPixmap.SP_BrowserReload),
                                      "Volver a leer")
        self.btn_releer.setShortcut(QKeySequence.StandardKey.Refresh)
        self.btn_releer.setToolTip("Lee la carpeta otra vez, por ejemplo después de corregir nombres")

        arriba = QHBoxLayout()
        arriba.addWidget(self.btn_carpeta)
        arriba.addWidget(self.campo_ruta, 1)
        arriba.addWidget(self.btn_releer)

        self.arbol = ArbolGrupos()
        self.arbol.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.lista_sin = ListaSinComprobante()
        self.lista_sin.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.arbol_invalidos = QTreeWidget()
        self.arbol_invalidos.setHeaderLabels(["Archivo", "Problema"])
        self.arbol_invalidos.setRootIsDecorated(False)
        self.arbol_invalidos.setColumnWidth(0, 260)
        self.lista_ignorados = QListWidget()

        self.pestanas = QTabWidget()
        self.pestanas.setDocumentMode(True)
        self.pestanas.addTab(self._con_ayuda(self.lista_sin,
            "Arrastre un soporte a un grupo de la izquierda para unirlo, "
            "o desde un grupo hasta aquí para sacarlo."), "")
        self.pestanas.addTab(self._con_ayuda(self.arbol_invalidos,
            "Corrija el nombre del archivo en la carpeta y pulse «Volver a leer»."), "")
        self.pestanas.addTab(self._con_ayuda(self.lista_ignorados,
            "Archivos que Kolontái no une (formatos no soportados)."), "")

        division = QSplitter()
        division.addWidget(self.arbol)
        division.addWidget(self.pestanas)
        division.setStretchFactor(0, 3)
        division.setStretchFactor(1, 1)
        division.setSizes([800, 440])

        self.btn_todos = QPushButton("Marcar todos")
        self.btn_ninguno = QPushButton("Desmarcar todos")
        self.resumen = QLabel()
        self.barra = QProgressBar()
        self.barra.setVisible(False)
        self.barra.setMaximumWidth(260)
        self.btn_salida = QPushButton(estilo.standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon),
                                      "Abrir carpeta de salida")
        self.btn_generar = QPushButton("Generar PDF")
        letra = QFont(self.btn_generar.font())
        letra.setBold(True)
        self.btn_generar.setFont(letra)
        self.btn_generar.setMinimumWidth(150)
        self.btn_generar.setDefault(True)

        abajo = QHBoxLayout()
        abajo.addWidget(self.btn_todos)
        abajo.addWidget(self.btn_ninguno)
        abajo.addSpacing(12)
        abajo.addWidget(self.resumen, 1)
        abajo.addWidget(self.barra)
        abajo.addWidget(self.btn_salida)
        abajo.addWidget(self.btn_generar)

        centro = QWidget()
        capas = QVBoxLayout(centro)
        capas.addLayout(arriba)
        capas.addWidget(division, 1)
        capas.addLayout(abajo)
        self.setCentralWidget(centro)

        self.btn_carpeta.clicked.connect(self.elegir_carpeta)
        self.btn_releer.clicked.connect(self.releer)
        self.btn_todos.clicked.connect(lambda: self._marcar_todos(True))
        self.btn_ninguno.clicked.connect(lambda: self._marcar_todos(False))
        self.btn_generar.clicked.connect(self.generar_pdf)
        self.btn_salida.clicked.connect(lambda: abrir(self.carpeta / CARPETA_SALIDA))
        self.arbol.soltado.connect(self.soltar)
        self.lista_sin.soltado.connect(self.soltar)
        self.arbol.itemChanged.connect(self._cambio_marca)
        self.arbol.itemDoubleClicked.connect(self._doble_clic)
        self.arbol.customContextMenuRequested.connect(self._menu_arbol)
        self.lista_sin.customContextMenuRequested.connect(self._menu_sin)
        self.lista_sin.itemDoubleClicked.connect(lambda i: abrir(i.data(ROL).ruta))
        self.arbol_invalidos.itemDoubleClicked.connect(lambda i, _c: abrir(i.data(0, ROL)))
        self.lista_ignorados.itemDoubleClicked.connect(lambda i: abrir(i.data(ROL)))

    @staticmethod
    def _con_ayuda(widget: QWidget, texto: str) -> QWidget:
        ayuda = QLabel(texto)
        ayuda.setWordWrap(True)
        ayuda.setEnabled(False)  # se ve atenuado, como texto secundario
        caja = QWidget()
        capas = QVBoxLayout(caja)
        capas.setContentsMargins(4, 6, 4, 4)
        capas.addWidget(ayuda)
        capas.addWidget(widget, 1)
        return caja

    def acerca_de(self) -> None:
        caja = QMessageBox(self)
        caja.setWindowTitle("Acerca de Kolontái")
        logo = QPixmap(str(RECURSOS / "kolontai.png"))
        if not logo.isNull():
            caja.setIconPixmap(logo.scaled(112, 112, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))
        caja.setTextFormat(Qt.TextFormat.RichText)
        caja.setText(
            f"<h3>Kolontái {__version__}</h3>"
            "<p>Une en un solo PDF los soportes contables de cada tercero.</p>"
            "<p>Copyright © 2026 Juan Sebastián Berrío Posada.</p>"
            "<p>Este programa es software libre: puede redistribuirlo y/o modificarlo "
            "bajo los términos de la Licencia Pública General GNU, versión 3 o "
            "posterior. Se distribuye <b>sin ninguna garantía</b>. Consulte el "
            "archivo LICENSE o <a href='https://www.gnu.org/licenses/gpl-3.0.html'>"
            "gnu.org/licenses/gpl-3.0</a>.</p>"
            "<p>El nombre y el logo rinden homenaje a Alexandra Kolontái (1872-1952).</p>")
        caja.exec()

    # ---------- carga ----------

    def elegir_carpeta(self) -> None:
        inicio = self.ajustes.value("ultima_carpeta", str(Path.home()))
        elegida = QFileDialog.getExistingDirectory(self, "Carpeta con los documentos del mes", inicio)
        if elegida:
            self.ajustes.setValue("ultima_carpeta", str(Path(elegida).parent))
            self.cargar(Path(elegida))

    def cargar(self, carpeta: Path) -> None:
        try:
            resultado = analizar(carpeta)
        except OSError as e:
            QMessageBox.critical(self, "No se pudo leer la carpeta", f"{carpeta}\n\n{e}")
            return
        self.carpeta, self.resultado = carpeta, resultado
        self.excluidos.clear()
        self.campo_ruta.setText(str(carpeta))
        self.setWindowTitle(f"Kolontái · {carpeta.name}")
        self.refrescar()

    def releer(self) -> None:
        if self.carpeta is None:
            return
        if self.resultado and any(g.revisado for g in self.resultado.grupos):
            r = QMessageBox.question(
                self, "Volver a leer",
                "Se perderán los cambios hechos a mano en los grupos. ¿Leer la carpeta otra vez?")
            if r != QMessageBox.StandardButton.Yes:
                return
        self.cargar(self.carpeta)

    # ---------- pintar ----------

    def _mostrar_vacio(self) -> None:
        self.resumen.setText("Elija una carpeta para empezar.")
        for i, nombre in enumerate(("Sin comprobante", "Fuera del estándar", "Ignorados")):
            self.pestanas.setTabText(i, nombre)
        self._habilitar(True)

    def refrescar(self) -> None:
        r = self.resultado
        if r is None:
            return self._mostrar_vacio()
        icono_ok = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        icono_aviso = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)

        self.arbol.blockSignals(True)
        self.arbol.clear()
        for g in r.grupos:
            # Los avisos sobre un documento puntual se muestran en su propia fila
            por_doc: dict[str, list[str]] = {}
            obs = []
            for aviso in g.observaciones:
                nombre, _, resto = aviso.partition(": ")
                if resto and any(d.nombre == nombre for d in g.documentos):
                    por_doc.setdefault(nombre, []).append(resto[:1].upper() + resto[1:])
                else:
                    obs.append(aviso)
            if por_doc or any(d.avisos for d in g.documentos):
                obs.append("Revise los documentos señalados")
            if g.revisado:
                obs.append("Revisado a mano")
            padre = QTreeWidgetItem([g.nombre_salida, f"{g.ancla.fecha:%d.%m.%Y}", "; ".join(obs)])
            padre.setData(0, ROL, g)
            padre.setFlags(padre.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            padre.setCheckState(0, Qt.CheckState.Unchecked if id(g) in self.excluidos
                                else Qt.CheckState.Checked)
            padre.setIcon(0, icono_aviso if g.revisar else icono_ok)
            padre.setToolTip(2, "\n".join(obs) or "Sin observaciones")
            letra = padre.font(0)
            letra.setBold(True)
            padre.setFont(0, letra)
            color = COLOR_REVISAR if g.revisar else COLOR_REVISADO if g.revisado else None
            for d in g.documentos:
                avisos = d.avisos + por_doc.get(d.nombre, [])
                hijo = QTreeWidgetItem([d.nombre, f"{d.fecha:%d.%m.%Y}", "; ".join(avisos)])
                if avisos:
                    hijo.setIcon(2, icono_aviso)
                    hijo.setToolTip(2, "\n".join(avisos))
                hijo.setData(0, ROL, d)
                hijo.setToolTip(0, f"{d.ruta}\nDoble clic para abrir")
                if color:
                    self._pintar(hijo, color)
                padre.addChild(hijo)
            if color:
                self._pintar(padre, color)
            self.arbol.addTopLevelItem(padre)
            padre.setExpanded(g.revisar)
        self.arbol.blockSignals(False)

        self.lista_sin.clear()
        for d in r.huerfanos:
            item = QListWidgetItem(d.nombre)
            item.setData(ROL, d)
            item.setToolTip("Doble clic para abrir · arrástrelo a un grupo para unirlo")
            self.lista_sin.addItem(item)

        self.arbol_invalidos.clear()
        for d in r.invalidos:
            item = QTreeWidgetItem([d.nombre, d.error])
            item.setData(0, ROL, d.ruta)
            item.setToolTip(1, d.error)
            self.arbol_invalidos.addTopLevelItem(item)

        self.lista_ignorados.clear()
        for p in r.ignorados:
            item = QListWidgetItem(p.name)
            item.setData(ROL, p)
            self.lista_ignorados.addItem(item)

        self.pestanas.setTabText(0, f"Sin comprobante ({len(r.huerfanos)})")
        self.pestanas.setTabText(1, f"Fuera del estándar ({len(r.invalidos)})")
        self.pestanas.setTabText(2, f"Ignorados ({len(r.ignorados)})")
        self._actualizar_resumen()

    @staticmethod
    def _pintar(item: QTreeWidgetItem, color: QColor) -> None:
        for col in range(3):
            item.setBackground(col, QBrush(color))
            item.setForeground(col, QBrush(COLOR_TEXTO))

    def _marcados(self) -> list[Grupo]:
        if self.resultado is None:
            return []
        return [g for g in self.resultado.grupos if id(g) not in self.excluidos]

    def _actualizar_resumen(self) -> None:
        r = self.resultado
        revisar = sum(g.revisar for g in r.grupos)
        partes = [f"{len(r.grupos)} grupos", f"{len(self._marcados())} para generar"]
        if revisar:
            partes.append(f"{revisar} por revisar")
        if r.huerfanos:
            partes.append(f"{len(r.huerfanos)} sin comprobante")
        if r.invalidos:
            partes.append(f"{len(r.invalidos)} fuera del estándar")
        self.resumen.setText(", ".join(partes) + ".")
        self._habilitar(True)

    def _habilitar(self, libre: bool) -> None:
        hay = self.resultado is not None
        self.btn_carpeta.setEnabled(libre)
        self.btn_releer.setEnabled(libre and hay)
        self.btn_todos.setEnabled(libre and hay)
        self.btn_ninguno.setEnabled(libre and hay)
        self.btn_generar.setEnabled(libre and hay and bool(self._marcados()))
        self.btn_salida.setEnabled(libre and hay and (self.carpeta / CARPETA_SALIDA).is_dir())
        self.arbol.setEnabled(libre)
        self.pestanas.setEnabled(libre)

    # ---------- edición ----------

    def _cambio_marca(self, item: QTreeWidgetItem, columna: int) -> None:
        grupo = item.data(0, ROL)
        if columna != 0 or not isinstance(grupo, Grupo):
            return
        if item.checkState(0) == Qt.CheckState.Checked:
            self.excluidos.discard(id(grupo))
        else:
            self.excluidos.add(id(grupo))
        self._actualizar_resumen()

    def _marcar_todos(self, marcar: bool) -> None:
        self.excluidos = set() if marcar else {id(g) for g in self.resultado.grupos}
        self.refrescar()

    def _buscar(self, ruta: str) -> Documento | None:
        r = self.resultado
        for d in r.huerfanos + [s for g in r.grupos for s in g.soportes]:
            if str(d.ruta) == ruta:
                return d
        return None

    def soltar(self, ruta: str, destino: Grupo | None) -> None:
        doc = self._buscar(ruta)
        if doc is None:
            return
        error = mover(self.resultado, doc, destino)
        if error:
            QMessageBox.warning(self, "No se puede mover", error)
        # Se repinta después de que Qt termine de procesar el arrastre
        QTimer.singleShot(0, self.refrescar)

    def _marcar_revisado(self, grupo: Grupo) -> None:
        grupo.revisado = True
        self.refrescar()

    def _submenu_mover(self, menu: QMenu, doc: Documento) -> None:
        sub = menu.addMenu("Mover a")
        actual = next((g for g in self.resultado.grupos if any(s is doc for s in g.soportes)), None)
        destinos = [g for g in compatibles(doc, self.resultado) if g is not actual]
        for g in destinos:
            sub.addAction(g.nombre_salida, lambda g=g: self.soltar(str(doc.ruta), g))
        sub.setEnabled(bool(destinos))

    def _menu_arbol(self, punto) -> None:
        item = self.arbol.itemAt(punto)
        if item is None:
            return
        obj = item.data(0, ROL)
        menu = QMenu(self)
        if isinstance(obj, Grupo):
            menu.addAction("Abrir comprobante", lambda: abrir(obj.ancla.ruta))
            if obj.revisar:
                menu.addAction("Marcar como revisado", lambda: self._marcar_revisado(obj))
        else:
            menu.addAction("Abrir archivo", lambda: abrir(obj.ruta))
            if obj.prefijo not in REGLAS:
                self._submenu_mover(menu, obj)
                menu.addAction("Sacar del grupo", lambda: self.soltar(str(obj.ruta), None))
        menu.exec(self.arbol.viewport().mapToGlobal(punto))

    def _menu_sin(self, punto) -> None:
        item = self.lista_sin.itemAt(punto)
        if item is None:
            return
        doc = item.data(ROL)
        menu = QMenu(self)
        menu.addAction("Abrir archivo", lambda: abrir(doc.ruta))
        self._submenu_mover(menu, doc)
        menu.exec(self.lista_sin.viewport().mapToGlobal(punto))

    def _doble_clic(self, item: QTreeWidgetItem, _columna: int) -> None:
        obj = item.data(0, ROL)
        if isinstance(obj, Documento):
            abrir(obj.ruta)

    # ---------- generación ----------

    def generar_pdf(self) -> None:
        grupos = self._marcados()
        if not grupos:
            return
        pendientes = sum(g.revisar for g in grupos)
        if pendientes:
            r = QMessageBox.question(
                self, "Grupos por revisar",
                f"{pendientes} de los grupos marcados tienen observaciones sin revisar.\n\n"
                "¿Generarlos de todos modos? Quedarán señalados en el reporte.")
            if r != QMessageBox.StandardButton.Yes:
                return

        self._habilitar(False)
        self.barra.setRange(0, len(grupos))
        self.barra.setValue(0)
        self.barra.setVisible(True)

        self.hilo = QThread(self)
        self.trabajador = Trabajador(self.resultado, self.carpeta, grupos)
        self.trabajador.moveToThread(self.hilo)
        self.hilo.started.connect(self.trabajador.run)
        self.trabajador.progreso.connect(self._progreso)
        self.trabajador.terminado.connect(self._terminado)
        self.trabajador.fallo.connect(self._fallo)
        self.trabajador.terminado.connect(self.hilo.quit)
        self.trabajador.fallo.connect(self.hilo.quit)
        self.hilo.finished.connect(self.trabajador.deleteLater)
        self.hilo.start()

    def _progreso(self, i: int, total: int, nombre: str) -> None:
        self.barra.setValue(i - 1)
        self.statusBar().showMessage(f"Generando {i} de {total}: {nombre}")

    def _terminado(self, salidas, reporte: Path) -> None:
        self.barra.setValue(self.barra.maximum())
        self.barra.setVisible(False)
        self.statusBar().clearMessage()
        self._habilitar(True)
        errores = [s for s in salidas if s.error]
        texto = f"Se generaron {len(salidas) - len(errores)} PDF en «{CARPETA_SALIDA}»."
        if errores:
            texto += f"\n\n{len(errores)} no se pudieron generar:\n" + "\n".join(
                f"• {s.grupo.nombre_salida}: {s.error}" for s in errores[:10])
        texto += f"\n\nEl detalle está en {reporte.name}."
        caja = QMessageBox(QMessageBox.Icon.Warning if errores else QMessageBox.Icon.Information,
                           "Generación terminada", texto, parent=self)
        btn_abrir = caja.addButton("Abrir carpeta de salida", QMessageBox.ButtonRole.AcceptRole)
        caja.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
        caja.exec()
        if caja.clickedButton() is btn_abrir:
            abrir(reporte.parent)

    def _fallo(self, mensaje: str) -> None:
        self.barra.setVisible(False)
        self.statusBar().clearMessage()
        self._habilitar(True)
        QMessageBox.critical(self, "No se pudo generar", mensaje)

    def closeEvent(self, evento) -> None:  # noqa: N802
        if self.hilo is not None and self.hilo.isRunning():
            QMessageBox.information(self, "Kolontái", "Espere a que termine la generación de los PDF.")
            evento.ignore()
        else:
            evento.accept()


def main(argv: list[str] | None = None) -> int:
    if sys.platform == "win32":
        # Para que Windows muestre el logo de Kolontái en la barra de tareas
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Kolontai.Kolontai")
        except Exception:
            pass
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("Kolontái")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(QIcon(str(RECURSOS / "kolontai.png")))
    app.setStyle("Fusion")
    ventana = Ventana()
    ventana.show()
    argumentos = app.arguments()[1:]
    if argumentos and Path(argumentos[0]).is_dir():
        ventana.cargar(Path(argumentos[0]))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
